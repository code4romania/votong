import logging
import mimetypes
import tempfile
from typing import Dict

import requests
from django.conf import settings
from django.core.files import File
from django_q.tasks import async_task
from pycognito import Cognito
from requests import Response

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


def get_ngo_hub_data(ngohub_org_id: int) -> Dict:
    token = authenticate_with_ngohub()
    auth_headers = {"Authorization": f"Bearer {token}"}

    request_url: str = settings.NGOHUB_API_BASE + f"/organization/{ngohub_org_id}"
    response: Response = requests.get(request_url, headers=auth_headers)

    return response.json()


def update_organization_process(organization_id: int):
    organization: Organization = Organization.objects.get(id=organization_id)

    ngohub_id: int = organization.ngohub_org_id
    ngohub_org_data: Dict = get_ngo_hub_data(ngohub_id)

    ngohub_general_data: Dict = ngohub_org_data.get("organizationGeneral", {})
    ngohub_legal_data: Dict = ngohub_org_data.get("organizationLegal", {})

    organization.county = ngohub_general_data.get("county", {}).get("name", "")
    city_name = ngohub_general_data.get("city", {}).get("name", "")
    try:
        city = City.objects.get(county=organization.county, city=city_name)
    except City.DoesNotExist:
        logger.error(f"ERROR: Cannot find city '{city_name}' in VotONG.")
    else:
        organization.city = city

    organization.name = ngohub_general_data.get("name", "")
    organization.address = ngohub_general_data.get("address", "")
    organization.registration_number = ngohub_general_data.get("rafNumber", "")

    # Import the organization logo
    logo_url: str = ngohub_general_data.get("logo", "")
    logo_filename: str = remove_signature(logo_url)
    if not logo_filename and organization.logo:
        organization.logo.delete()
    elif logo_filename != organization.filename_cache.get("logo", ""):
        r: Response = requests.get(logo_url)
        if r.status_code != 200:
            logger.info("Logo file request status = %s", r.status_code)
        else:
            ext = mimetypes.guess_extension(r.headers["content-type"])
            with tempfile.TemporaryFile() as fp:
                fp.write(r.content)
                fp.seek(0)
                organization.logo.save(f"logo{ext}", File(fp))
            organization.filename_cache["logo"] = logo_filename

    # Import the organization statute
    statute_url: str = ngohub_legal_data.get("organizationStatute", "")
    statute_filename: str = remove_signature(statute_url)
    if not statute_filename and organization.statute:
        organization.statute.delete()
    elif statute_filename != organization.filename_cache.get("statute", ""):
        r: Response = requests.get(statute_url)
        if r.status_code != 200:
            logger.info("Statute file request status = %s", r.status_code)
        else:
            ext = mimetypes.guess_extension(r.headers["content-type"])
            with tempfile.TemporaryFile() as fp:
                fp.write(r.content)
                fp.seek(0)
                organization.statute.save(f"statute{ext}", File(fp))
            organization.filename_cache["statute"] = statute_filename

    organization.email = ngohub_general_data.get("email", "")
    organization.phone = ngohub_general_data.get("phone", "")
    organization.description = ngohub_general_data.get("description", "")

    organization.legal_representative_name = ngohub_legal_data.get("legalReprezentative", {}).get("fullName", "")
    organization.legal_representative_email = ngohub_legal_data.get("legalReprezentative", {}).get("email", "")
    organization.legal_representative_phone = ngohub_legal_data.get("legalReprezentative", {}).get("phone", "")

    organization.board_council = ", ".join(
        [director.get("fullName", "") for director in ngohub_legal_data.get("directors", [])]
    )

    organization.organization_head_name = (
        "" if not organization.organization_head_name else organization.organization_head_name
    )

    if organization.status == Organization.STATUS.draft:
        organization.status = Organization.STATUS.pending

    organization.save()


def update_organization(organization_id: int):
    """
    Update the organization with the given ID asynchronously.
    """

    async_task(update_organization_process, organization_id)
