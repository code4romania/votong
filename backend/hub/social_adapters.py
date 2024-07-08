import mimetypes
import requests
import tempfile

from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialLogin
from allauth.socialaccount.signals import pre_social_login, social_account_updated
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.files import File
from django.dispatch import receiver
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _

from accounts.models import User
from hub.exceptions import DuplicateOrganizationException, MissingOrganizationException, ClosedRegistrationException
from hub.models import Organization, NGO_GROUP, City, FeatureFlag


class UserOrgAdapter(DefaultSocialAccountAdapter):
    """
    Authentication adapter which makes sure that each new User also has an Organization
    """

    def save_user(self, request: HttpRequest, sociallogin: SocialLogin, form=None) -> User:
        """
        Besides the default user creation, also mark this user as coming from NGO Hub,
        create a blank Organization for them, and schedule a data update from NGO Hub.
        """

        user: User = super().save_user(request, sociallogin, form)
        user.is_ngohub_user = True
        user.save()

        # Add the user to the NGO group
        ngo_group: Group = Group.objects.get(name=NGO_GROUP)
        user.groups.add(ngo_group)

        # Create a blank Organization for the newly registered user
        org = create_blank_org(user)

        # Start the import of initial data from NGO Hub
        update_user_org(org, sociallogin.token, in_auth_flow=True)

        return user


def create_blank_org(user, commit=True) -> Organization:
    """
    Create a blank Organization (with a draft status) for an User
    """

    org = Organization(user=user, accept_terms_and_conditions=True, status=Organization.STATUS.draft)
    if commit:
        org.save()

    return org


def remove_signature(s3_url: str) -> str:
    """
    Extract the S3 file name without the URL signature and the directory path
    """
    if s3_url:
        return s3_url.split("?")[0].split("/")[-1]
    else:
        return ""


def update_user_org(org: Organization, token: str, *, in_auth_flow: bool = False) -> None:
    """
    Update an Organization by pulling data from NGO Hub.

    If this happens in an auth flow, raise an ImmediateHttpResponse in case of errors in order to
    redirect the user to a relevant error page.
    """

    if not FeatureFlag.flag_enabled("enable_org_registration"):
        if in_auth_flow:
            raise ImmediateHttpResponse(redirect(reverse("error-org-registration-closed")))
        else:
            raise ClosedRegistrationException(
                _("The registration process for new organizations is currently disabled.")
            )

    if not org.filename_cache:
        org.filename_cache = {}

    auth_headers = {"Authorization": f"Bearer {token}"}

    # ngohub_user = requests.get(settings.NGOHUB_API_BASE + "api/ong-user/", headers=auth_headers).json()
    # print(ngohub_user)

    ngohub_org = requests.get(settings.NGOHUB_API_BASE + "organization-profile/", headers=auth_headers).json()

    # Check that an NGO Hub organization appears only once in VotONG
    ngohub_id = ngohub_org.get("id", 0)
    if not ngohub_id:
        if in_auth_flow:
            raise ImmediateHttpResponse(redirect(reverse("error-org-missing")))
        else:
            raise MissingOrganizationException(_("There is no NGO Hub organization for this VotONG user."))

    # Check that the current user has an NGO Hub organization
    if Organization.objects.filter(ngohub_org_id=ngohub_id).exclude(pk=org.pk).count():
        if in_auth_flow:
            raise ImmediateHttpResponse(redirect(reverse("error-org-duplicate")))
        else:
            raise DuplicateOrganizationException(_("This NGO Hub organization already exists for another VotONG user."))

    org.ngohub_org_id = ngohub_id
    ngohub_general = ngohub_org.get("organizationGeneral", {})
    ngohub_legal = ngohub_org.get("organizationLegal", {})

    org.county = ngohub_general.get("county", {}).get("name", "")
    city_name = ngohub_general.get("city", {}).get("name", "")
    try:
        city = City.objects.get(county=org.county, city=city_name)
    except City.DoesNotExist:
        print("ERROR: Cannot find city '", city, "' in VotONG.")
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

    # TODO:
    org.organization_head_name = ""

    if org.status == Organization.STATUS.draft:
        org.status = Organization.STATUS.pending

    org.save()


@receiver(social_account_updated)
def handle_existing_login(sender: SocialLogin, **kwargs) -> None:
    """
    Handler for the social-account-update signal, which is sent for all logins
    after the initial login.

    We already have an User, but we must be sure that the User also has
    an Organization and schedule its data update from NGO Hub.
    """

    social = kwargs.get("sociallogin")
    org = Organization.objects.filter(user=social.user).last()
    if not org:
        org = create_blank_org(social.user)

    update_user_org(org, social.token, in_auth_flow=True)


@receiver(pre_social_login)
def handle_pre_login(sender: SocialLogin, **kwargs) -> None:
    """
    Handler for the pre-login signal
    IMPORTANT: The User object might not be fully available here.
    """

    # social = kwargs.get("sociallogin")
    # request = kwargs.get("request")
    #
    # print("code =", request.GET.get("code"))
    # print("user =", social.user)
    # print("token =", social.token)

    pass
