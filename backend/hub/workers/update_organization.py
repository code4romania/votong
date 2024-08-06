import logging
import mimetypes
import tempfile
from typing import Dict, List, Optional

import requests
from django.conf import settings
from django.core.files import File
from django.utils import timezone
from django_q.models import Schedule
from django_q.tasks import async_task
from pycognito import Cognito
from requests import Response

from accounts.models import STAFF_GROUP, SUPPORT_GROUP, User
from civil_society_vote.common.cache import cache_decorator
from civil_society_vote.common.messaging import send_email
from hub.exceptions import NGOHubHTTPException
from hub.models import City, Organization
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


ORGANIZATION_UPDATE_SCHEDULE_ID = "ORGANIZATION-UPDATE-SCHEDULE"


def remove_signature(s3_url: str) -> str:
    """
    Extract the S3 file name without the URL signature and the directory path
    """
    if s3_url:
        return s3_url.split("?")[0].split("/")[-1]
    else:
        return ""


def copy_file_to_organization(organization: Organization, signed_file_url: str, file_type: str):
    if not hasattr(organization, file_type):
        raise AttributeError(f"Organization has no attribute '{file_type}'")

    filename: str = remove_signature(signed_file_url)
    if not filename and getattr(organization, file_type):
        getattr(organization, file_type).delete()
        error_message = f"ERROR: {file_type.upper()} file URL is empty, deleting the existing file."
        logger.error(error_message)
        return error_message

    if not filename:
        error_message = f"ERROR: {file_type.upper()} file URL is empty, but is a required field."
        logger.error(error_message)
        return error_message

    if filename == organization.filename_cache.get(file_type, ""):
        logger.info(f"{file_type.upper()} file is already up to date.")
        return None

    r: Response = requests.get(signed_file_url)
    if r.status_code != requests.codes.ok:
        logger.info(f"{file_type.upper()} file request status = {r.status_code}")
        error_message = f"ERROR: Could not download {file_type} file from NGO Hub, error status {r.status_code}."
        logger.error(error_message)
        return error_message

    extension: str = mimetypes.guess_extension(r.headers["content-type"])
    # TODO: mimetypes thinks that some S3 documents are .bin files, which is useless
    if extension == ".bin":
        extension = ""
    with tempfile.TemporaryFile() as fp:
        fp.write(r.content)
        fp.seek(0)
        getattr(organization, file_type).save(f"{file_type}{extension}", File(fp))

    organization.filename_cache[file_type] = filename


@cache_decorator(timeout=settings.TIMEOUT_CACHE_NORMAL, cache_key="authenticate_with_ngohub")
def authenticate_with_ngohub() -> str:
    u = Cognito(
        user_pool_id=settings.AWS_COGNITO_USER_POOL_ID,
        client_id=settings.AWS_COGNITO_CLIENT_ID,
        client_secret=settings.AWS_COGNITO_CLIENT_SECRET,
        username=settings.NGOHUB_API_ACCOUNT,
        user_pool_region=settings.AWS_COGNITO_REGION,
    )
    u.authenticate(password=settings.NGOHUB_API_KEY)

    return u.id_token


def get_ngo_hub_data(ngohub_org_id: int, token: str = "") -> Dict:

    # if a token is already provided, use it for the profile endpoint
    if token:
        request_url: str = settings.NGOHUB_API_BASE + "organization-profile/"

    # if no token is provided, attempt to authenticate as an admin for the organization endpoint
    else:
        token: str = authenticate_with_ngohub()
        request_url: str = settings.NGOHUB_API_BASE + f"/organization/{ngohub_org_id}"

    auth_headers = {"Authorization": f"Bearer {token}"}
    response: Response = requests.get(request_url, headers=auth_headers)

    if response.status_code != requests.codes.ok:
        raise NGOHubHTTPException

    return response.json()


def update_organization_process(organization_id: int, token: str = ""):
    errors: List[str] = []

    organization: Organization = Organization.objects.get(id=organization_id)

    organization.ngohub_last_update_started = timezone.now()
    organization.save()

    if not organization.filename_cache:
        organization.filename_cache = {}

    ngohub_id: int = organization.ngohub_org_id
    ngohub_org_data: Dict = get_ngo_hub_data(ngohub_id, token)

    ngohub_general_data: Dict = ngohub_org_data.get("organizationGeneral", {})
    ngohub_legal_data: Dict = ngohub_org_data.get("organizationLegal", {})

    organization.county = ngohub_general_data.get("county", {}).get("name") or ""
    city_name = ngohub_general_data.get("city", {}).get("name") or ""
    try:
        city = City.objects.get(county=organization.county, city=city_name)
    except City.DoesNotExist:
        error_message: str = f"ERROR: Cannot find city '{city_name}' received from NGO Hub in VotONG."
        errors.append(error_message)
        logger.error(error_message)
    else:
        organization.city = city

    organization.name = ngohub_general_data.get("name") or ""
    organization.address = ngohub_general_data.get("address") or ""
    organization.registration_number = ngohub_general_data.get("rafNumber") or ""

    # Import the organization logo
    logo_url: str = ngohub_general_data.get("logo") or ""
    logo_url_error: Optional[str] = copy_file_to_organization(organization, logo_url, "logo")
    if logo_url_error:
        errors.append(logo_url_error)

    # Import the organization statute
    statute_url: str = ngohub_legal_data.get("organizationStatute") or ""
    statute_url_error: Optional[str] = copy_file_to_organization(organization, statute_url, "statute")
    if statute_url_error:
        errors.append(statute_url_error)

    # Import the organization nonPoliticalAffiliationFile
    non_political_affiliation_url: str = ngohub_legal_data.get("nonPoliticalAffiliationFile") or ""
    non_political_affiliation_url_error: Optional[str] = copy_file_to_organization(
        organization, non_political_affiliation_url, "statement_political"
    )
    if non_political_affiliation_url_error:
        errors.append(non_political_affiliation_url_error)

    # Import the organization balance sheet
    balance_sheet_url: str = ngohub_legal_data.get("balanceSheet") or ""
    balance_sheet_url_error: Optional[str] = copy_file_to_organization(
        organization, balance_sheet_url, "last_balance_sheet"
    )
    if balance_sheet_url_error:
        errors.append(balance_sheet_url_error)

    organization.email = ngohub_general_data.get("email") or ""
    organization.phone = ngohub_general_data.get("phone") or ""
    organization.description = ngohub_general_data.get("description") or ""

    organization.legal_representative_name = ngohub_legal_data.get("legalReprezentative", {}).get("fullName") or ""
    organization.legal_representative_email = ngohub_legal_data.get("legalReprezentative", {}).get("email") or ""
    organization.legal_representative_phone = ngohub_legal_data.get("legalReprezentative", {}).get("phone") or ""

    board_council: List[str] = []
    for director in ngohub_legal_data.get("directors", []):
        director_name: str = director.get("fullName")
        director_role: str = director.get("role")

        if director_name and director_role:
            board_council.append(f"{director_name} ({director_role})")
        elif director_name:
            board_council.append(director_name)
        else:
            errors.append("ERROR: Director name is missing in the data received from NGO Hub.")

    organization.board_council = ", ".join(board_council)

    if organization.status in (Organization.STATUS.draft, Organization.STATUS.pending):
        organization.status = Organization.STATUS.accepted if not errors else Organization.STATUS.pending

    organization.ngohub_last_update_ended = timezone.now()

    organization.save()

    task_result: Dict[str, any] = {"organization_id": organization_id}
    if errors:
        task_result["errors"] = errors

        subject: str = _("Error updating organization") + f" {organization.name}" if organization.name else ""
        to_emails: List[str] = User.objects.filter(groups__name__in=(STAFF_GROUP, SUPPORT_GROUP)).values_list(
            "email", flat=True
        )

        send_email(
            subject=subject,
            to_emails=to_emails,
            text_template="hub/emails/07_importing_errors.txt",
            html_template="hub/emails/07_importing_errors.html",
            context={
                "ngo_name": organization.name,
                "ngo_url": f"{settings.VOTONG_WEBSITE}/{organization.get_absolute_url()}",
                "errors": errors,
            },
        )

    return task_result


def update_organization(organization_id: int, token: str = ""):
    """
    Update the organization with the given ID asynchronously.
    """
    if settings.UPDATE_ORGANIZATION_METHOD == "async":
        async_task(update_organization_process, organization_id, token)
    else:
        update_organization_process(organization_id, token)


def update_outdated_organizations():
    """
    Update a threshold of organizations that have not been updated in the last 7 days.
    """
    limit: int = settings.ORGANIZATION_UPDATE_THRESHOLD or 10
    organizations_per_week: int = limit * 24 * 7
    if (organizations_count := Organization.objects.count()) >= organizations_per_week:
        logger.error(
            f"There are {organizations_count} organizations to update "
            f"but only {organizations_per_week} can be processed weekly. "
            f"Please increase the threshold from {limit} to allow all organizations to be updated."
        )

    last_7_days = timezone.now() - timezone.timedelta(days=7)
    accepted_statuses = (Organization.STATUS.accepted, Organization.STATUS.pending)
    organizations = Organization.objects.filter(
        modified__lte=last_7_days,
        status__in=accepted_statuses,
    ).order_by(
        "modified"
    )[:limit]

    organizations_ids: List[int] = []
    if not organizations:
        logger.info("No outdated organizations found.")
        return organizations_ids

    for organization in organizations:
        logger.info(f"Starting update for organization {organization.id}")
        update_organization(organization.id)

        organizations_ids.append(organization.id)

    logger.info(f"Updated {len(organizations)} organizations.")

    return organizations_ids


def start_organization_update_schedule():
    """
    Schedule a task to update organizations to run at 10 minutes past every hour.

    Delete any existing such tasks before adding the new schedule.
    """
    Schedule.objects.filter(name=ORGANIZATION_UPDATE_SCHEDULE_ID).delete()

    cron_every_hour_at_past_10 = "45 */1 * * *"

    Schedule.objects.get_or_create(
        name=ORGANIZATION_UPDATE_SCHEDULE_ID,
        func="hub.workers.update_organization.update_outdated_organizations",
        schedule_type=Schedule.CRON,
        cron=cron_every_hour_at_past_10,
        repeats=-1,
        next_run=timezone.now() + timezone.timedelta(seconds=30),
    )
