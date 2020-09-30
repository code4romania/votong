from accounts.views import ChangeAvatarView, ChangeEmailView, PasswordResetView
from django.urls import path
from django.utils.translation import ugettext_lazy as _

urlpatterns = [
    path(_("password-reset/"), PasswordResetView.as_view(), name="account-password-reset"),
    path(_("change-avatar/"), ChangeAvatarView.as_view(), name="account-change-avatar"),
    path(_("change-email/"), ChangeEmailView.as_view(), name="account-change-email"),
]
