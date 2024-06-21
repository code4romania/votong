from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import Group

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
