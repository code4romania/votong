import requests

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.signals import pre_social_login, social_account_updated
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
        org = Organization(user=user, status=Organization.STATUS.accepted)
        org.save()

        return user


def update_user_org(sender, **kwargs):
    print("UPDATING USER ORG")

    social = kwargs.get("sociallogin")
    # request = kwargs.get("request")

    # print("code =", request.GET.get("code"))
    # print("user =", social.user)
    # print("token =", social.token)
    auth_headers = {"Authorization": f"Bearer {social.token}"}

    response = requests.get(settings.NGOHUB_API_BASE + "api/ong-user/", headers=auth_headers)
    print(response.json())

    response = requests.get(settings.NGOHUB_API_BASE + "organization-profile/", headers=auth_headers)
    print(response.json())


social_account_updated.connect(update_user_org)
pre_social_login.connect(update_user_org)
