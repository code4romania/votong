import requests

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.signals import pre_social_login, social_account_updated

# from allauth.socialaccount.models import SocialToken, SocialAccount
from django.contrib.auth.models import Group
from django.conf import settings
from django.dispatch import receiver

from .models import Organization, NGO_GROUP


class UserOrgAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        print("CREATE USER")

        user = super().save_user(request, sociallogin, form)
        user.is_ngohub_user = True
        user.save()

        # Add the user to the NGO group
        ngo_group = Group.objects.get(name=NGO_GROUP)
        user.groups.add(ngo_group)

        # Create a blank Organization for the newly registered user
        org = create_blank_org(user)

        # Start the import of initial data from NGO Hub
        update_user_org(org, sociallogin.token)

        return user


def create_blank_org(user, commit=True):
    print("CREATE USER ORG")

    org = Organization(user=user, accept_terms_and_conditions=True, status=Organization.STATUS.pending)
    if commit:
        org.save()
    return org


def update_user_org(org: Organization, token: str):
    print("UPDATE USER ORG")

    auth_headers = {"Authorization": f"Bearer {token}"}
    # response = requests.get(settings.NGOHUB_API_BASE + "api/ong-user/", headers=auth_headers)
    # print(response.json())

    ngohub_org = requests.get(settings.NGOHUB_API_BASE + "organization-profile/", headers=auth_headers).json()

    org.ngohub_org_id = ngohub_org["id"]
    org.name = ngohub_org["organizationGeneral"]["name"]
    # org.county = ""
    # org.city = ""
    org.address = ngohub_org["organizationGeneral"]["address"]
    org.registration_number = ngohub_org["organizationGeneral"]["rafNumber"]

    org.logo_url = ngohub_org["organizationGeneral"]["logo"]
    if org.logo:
        org.logo.delete()

    org.email = ngohub_org["organizationGeneral"]["email"]
    org.phone = ngohub_org["organizationGeneral"]["phone"]
    org.description = ngohub_org["organizationGeneral"]["description"]

    org.legal_representative_name = ngohub_org["organizationLegal"]["legalReprezentative"]["fullName"]
    org.legal_representative_email = ngohub_org["organizationLegal"]["legalReprezentative"]["email"]
    org.legal_representative_phone = ngohub_org["organizationLegal"]["legalReprezentative"]["phone"]

    org.board_council = ", ".join([director["fullName"] for director in ngohub_org["organizationLegal"]["directors"]])

    # TODO:
    org.organisation_head_name = ""

    org.save()


@receiver(social_account_updated)
def handle_existing_login(sender, **kwargs):
    print("HANDLE EXISTING LOGIN")

    social = kwargs.get("sociallogin")
    org = Organization.objects.filter(user=social.user).last()
    if not org:
        org = create_blank_org(social.user)

    return update_user_org(org, social.token)


@receiver(pre_social_login)
def handle_pre_login(sender, **kwargs):
    # IMPORTANT: The User object might not be fully available here!

    print("HANDLE PRE LOGIN")

    social = kwargs.get("sociallogin")
    # request = kwargs.get("request")
    # print("code =", request.GET.get("code"))
    # print("user =", social.user)

    print("token =", social.token)
