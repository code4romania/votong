from accounts.views import ChangeEmailView, CommissionMemberInviteView, PasswordResetView
from django.urls import include, path
from django.utils.translation import gettext_lazy as _

urlpatterns = [
    path(_("password-reset/"), PasswordResetView.as_view(), name="account-password-reset"),
    path(_("change-avatar/"), include("avatar.urls")),
    path(_("change-email/"), ChangeEmailView.as_view(), name="account-change-email"),
    path(_("invite-commission/"), CommissionMemberInviteView.as_view(), name="admin-invite-commission"),
]
