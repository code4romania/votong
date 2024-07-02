import requests

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.signals import pre_social_login, social_account_updated

# from allauth.socialaccount.models import SocialToken, SocialAccount
from django.contrib.auth.models import Group
from django.conf import settings

from .models import Organization, NGO_GROUP


class UserOrgAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)

        # Add the user to the NGO group
        ngo_group = Group.objects.get(name=NGO_GROUP)
        user.groups.add(ngo_group)

        # Create a blank Organization for the newly registered User
        org = Organization(user=user, accept_terms_and_conditions=True, status=Organization.STATUS.accepted)
        org.save()

        return user


def update_user_org(sender, **kwargs):
    print("UPDATING USER ORG")

    social = kwargs.get("sociallogin")
    # request = kwargs.get("request")

    # print("code =", request.GET.get("code"))
    # print("user =", social.user)
    print("token =", social.token)

    auth_headers = {"Authorization": f"Bearer {social.token}"}
    # response = requests.get(settings.NGOHUB_API_BASE + "api/ong-user/", headers=auth_headers)
    # print(response.json())

    ngohub_org = requests.get(settings.NGOHUB_API_BASE + "organization-profile/", headers=auth_headers).json()
    print(ngohub_org)

    org = Organization.objects.filter(user=social.user)[0]
    org.ngohub_org_id = ngohub_org["id"]
    org.name = ngohub_org["organizationGeneral"]["name"]
    # org.county = ""
    # org.city = ""
    org.address = ngohub_org["organizationGeneral"]["address"]
    org.registration_number = ngohub_org["organizationGeneral"]["rafNumber"]

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


social_account_updated.connect(update_user_org)
pre_social_login.connect(update_user_org)
