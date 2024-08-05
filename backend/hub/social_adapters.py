import logging
from typing import Dict

import requests
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialLogin
from allauth.socialaccount.signals import pre_social_login, social_account_updated
from django.conf import settings
from django.contrib.auth.models import Group
from django.dispatch import receiver
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _

from accounts.models import User
from hub.exceptions import (
    ClosedRegistrationException,
    DuplicateOrganizationException,
    MissingOrganizationException,
    NGOHubHTTPException,
)
from hub.models import FeatureFlag, NGO_GROUP, Organization, STAFF_GROUP
from hub.workers.update_organization import update_organization

logger = logging.getLogger(__name__)


def ngohub_api_get(path: str, token: str):
    """
    Perform a GET request to the NGO Hub API and return a JSON response, or raise NGOHubHTTPException
    """
    auth_headers = {"Authorization": f"Bearer {token}"}
    api_url = settings.NGOHUB_API_BASE + path

    response = requests.get(api_url, headers=auth_headers)
    if response.status_code != requests.codes.ok:
        print(api_url)
        logger.error("%s while retrieving %s", response.status_code, api_url)
        raise NGOHubHTTPException

    return response.json()


def update_user_org(org: Organization, token: str, *, in_auth_flow: bool = False) -> None:
    """
    Update an Organization by pulling data from NGO Hub.

    If this happens in an auth flow, raise an ImmediateHttpResponse in case of errors to
    redirect the user to a relevant error page.
    """

    # Check if the new organization registration is still open
    if org.status == Organization.STATUS.draft and not FeatureFlag.flag_enabled("enable_org_registration"):
        if in_auth_flow:
            raise ImmediateHttpResponse(redirect(reverse("error-org-registration-closed")))
        else:
            raise ClosedRegistrationException(
                _("The registration process for new organizations is currently disabled.")
            )

    # If the current organization is not already linked to NGO Hub, check the NGO Hub API for the data
    if not org.ngohub_org_id:
        ngohub_org = ngohub_api_get("organization-profile/", token)

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
                raise DuplicateOrganizationException(
                    _("This NGO Hub organization already exists for another VotONG user.")
                )

        org.status = Organization.STATUS.accepted

        org.ngohub_org_id = ngohub_id
        org.save()
    elif org.status == Organization.STATUS.pending:
        org.status = Organization.STATUS.accepted
        org.save()

    update_organization(org.id, token)


def check_app_enabled_in_ngohub(token: str) -> bool:
    response = ngohub_api_get("organizations/application/", token)
    for app in response:
        if (
            app["loginLink"].startswith(settings.VOTONG_WEBSITE)
            and app["status"] == "active"
            and app["ongStatus"] == "active"
        ):
            return True

    return False


def create_blank_org(user, commit=True) -> Organization:
    """
    Create a blank Organization (with a draft status) for a User
    """

    org = Organization(user=user, accept_terms_and_conditions=True, status=Organization.STATUS.draft)
    if commit:
        org.save()

    return org


def update_user_information(user: User, token: str):
    try:
        user_profile: Dict = ngohub_api_get("profile/", token)
    except NGOHubHTTPException:
        user_profile = {}

    user_role: str = user_profile.get("role", "")

    # Check the user role from NGO Hub
    if user_role == settings.NGOHUB_ROLE_SUPER_ADMIN:
        # A super admin from NGO Hub will become a Django admin on VotONG
        if user.orgs.exists():
            user.orgs.all().delete()

        user.first_name = user_profile.get("name", "")
        user.is_superuser = True
        user.is_staff = True
        user.save()

        user.groups.add(Group.objects.get(name=STAFF_GROUP))
        user.groups.remove(Group.objects.get(name=NGO_GROUP))
        return None

    elif user_role == settings.NGOHUB_ROLE_NGO_ADMIN:
        if not check_app_enabled_in_ngohub(token):
            user.orgs.all().delete()
            user.delete()

            if user.is_active:
                user.is_active = False
                user.save()

            raise ImmediateHttpResponse(redirect(reverse("error-app-missing")))
        elif not user.is_active:
            user.is_active = True
            user.save()

        # Add the user to the NGO group
        ngo_group: Group = Group.objects.get(name=NGO_GROUP)
        user.groups.add(ngo_group)

        org = Organization.objects.filter(user=user).first()
        if not org:
            org = create_blank_org(user)

        return org

    elif user_role == settings.NGOHUB_ROLE_NGO_EMPLOYEE:
        # Employees cannot have organizations
        raise ImmediateHttpResponse(redirect(reverse("error-user-role")))

    else:
        # Unknown user role
        raise ImmediateHttpResponse(redirect(reverse("error-unknown-user-role")))


def common_user_init(sociallogin: SocialLogin) -> User:
    user = sociallogin.user
    if user.is_superuser:
        return user

    # Create a blank Organization for the newly registered user
    org = update_user_information(user, sociallogin.token.token)

    # Start the import of initial data from NGO Hub
    if org:
        update_user_org(org, sociallogin.token.token, in_auth_flow=True)

    return user


class UserOrgAdapter(DefaultSocialAccountAdapter):
    """
    Authentication adapter which makes sure that each new `User` also has an `Organization`
    """

    def save_user(self, request: HttpRequest, sociallogin: SocialLogin, form=None) -> User:
        """
        Besides the default user creation, also mark this user as coming from NGO Hub,
        create a blank Organization for them, and schedule a data update from NGO Hub.
        """

        user: User = super().save_user(request, sociallogin, form)
        user.is_ngohub_user = True
        user.save()

        return common_user_init(sociallogin=sociallogin)


@receiver(social_account_updated)
def handle_existing_login(sociallogin: SocialLogin, **kwargs) -> None:
    """
    Handler for the social-account-update signal, which is sent for all logins after the initial login.

    We already have a User, but we must be sure that the User also has
    an Organization and schedule its data update from NGO Hub.
    """

    common_user_init(sociallogin=sociallogin)


@receiver(pre_social_login)
def handle_pre_login(**kwargs) -> None:
    """
    Handler for the pre-login signal
    IMPORTANT: The User object might not be fully available here.
    """

    pass
