import logging
import mimetypes
import tempfile

import requests
from django.conf import settings
from django.core.files import File
from django_q.tasks import async_task
from pycognito import Cognito

from hub.models import City, Organization

logger = logging.getLogger(__name__)


def remove_signature(s3_url: str) -> str:
    """
    Extract the S3 file name without the URL signature and the directory path
    """
    if s3_url:
        return s3_url.split("?")[0].split("/")[-1]
    else:
        return ""


def authenticate_with_ngohub():
    u = Cognito(
        user_pool_id=settings.AWS_COGNITO_USER_POOL_ID,
        client_id=settings.AWS_COGNITO_CLIENT_ID,
        client_secret=settings.AWS_COGNITO_CLIENT_SECRET,
        username=settings.NGOHUB_API_ACCOUNT,
    )
    u.authenticate(password=settings.NGOHUB_API_KEY)

    return u.id_token


def get_ngo_hub_data(ngohub_org_id: int):
    token = authenticate_with_ngohub()
    auth_headers = {"Authorization": f"Bearer {token}"}

    request_url: str = settings.NGOHUB_API_BASE + f"/organization/{ngohub_org_id}"
    response = requests.get(request_url, headers=auth_headers)

    return response.json()


def update_organization_process(organization_id: int):
    org: Organization = Organization.objects.get(id=organization_id)

    ngohub_id: int = org.ngohub_org_id
    ngohub_org = get_ngo_hub_data(ngohub_id)

    ngohub_general = ngohub_org.get("organizationGeneral", {})
    ngohub_legal = ngohub_org.get("organizationLegal", {})

    org.county = ngohub_general.get("county", {}).get("name", "")
    city_name = ngohub_general.get("city", {}).get("name", "")
    try:
        city = City.objects.get(county=org.county, city=city_name)
    except City.DoesNotExist:
        logger.error(f"ERROR: Cannot find city '{city_name}' in VotONG.")
    else:
        org.city = city

    org.name = ngohub_general.get("name", "")
    org.address = ngohub_general.get("address", "")
    org.registration_number = ngohub_general.get("rafNumber", "")

    # Import the organization logo
    logo_url = ngohub_general.get("logo", "")
    logo_filename = remove_signature(logo_url)
    if not logo_filename and org.logo:
        org.logo.delete()
    elif logo_filename != org.filename_cache.get("logo", ""):
        r = requests.get(logo_url)
        if r.status_code != 200:
            print("Logo file request status = %s", r.status_code)
        else:
            ext = mimetypes.guess_extension(r.headers["content-type"])
            with tempfile.TemporaryFile() as fp:
                fp.write(r.content)
                fp.seek(0)
                org.logo.save(f"logo{ext}", File(fp))
            org.filename_cache["logo"] = logo_filename

    # Import the organization statute
    statute_url = ngohub_legal.get("organizationStatute", "")
    statute_filename = remove_signature(statute_url)
    if not statute_filename and org.statute:
        org.statute.delete()
    elif statute_filename != org.filename_cache.get("statute", ""):
        r = requests.get(statute_url)
        if r.status_code != 200:
            print("Statute file request status = %s", r.status_code)
        else:
            ext = mimetypes.guess_extension(r.headers["content-type"])
            with tempfile.TemporaryFile() as fp:
                fp.write(r.content)
                fp.seek(0)
                org.statute.save(f"statute{ext}", File(fp))
            org.filename_cache["statute"] = statute_filename

    org.email = ngohub_general.get("email", "")
    org.phone = ngohub_general.get("phone", "")
    org.description = ngohub_general.get("description", "")

    org.legal_representative_name = ngohub_legal.get("legalReprezentative", {}).get("fullName", "")
    org.legal_representative_email = ngohub_legal.get("legalReprezentative", {}).get("email", "")
    org.legal_representative_phone = ngohub_legal.get("legalReprezentative", {}).get("phone", "")

    org.board_council = ", ".join([director.get("fullName", "") for director in ngohub_legal.get("directors", [])])

    org.organization_head_name = "" if not org.organization_head_name else org.organization_head_name

    if org.status == Organization.STATUS.draft:
        org.status = Organization.STATUS.pending

    org.save()


def update_organization(organization_id: int):
    """
    Update the organization with the given ID asynchronously.
    """

    async_task(update_organization_process, organization_id)
