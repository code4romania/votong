from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import Organization


class UserOrgAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)

        # Create a blank Organization for the newly registered User
        org = Organization(user=user, status=Organization.STATUS.accepted)
        org.save()

        return user
