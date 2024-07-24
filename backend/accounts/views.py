from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import FormView

from accounts.forms import InviteCommissionForm, UpdateEmailForm
from accounts.models import User
from hub.models import STAFF_GROUP, SUPPORT_GROUP


class PasswordResetView(auth_views.PasswordChangeView):
    template_name = "password-reset.html"
    success_url = reverse_lazy("account-password-reset")

    def form_valid(self, form):
        if self.request.user.is_ngohub_user:
            raise PermissionDenied(_("You cannot change the password for an NGO Hub account"))

        result = super().form_valid(form)

        messages.success(self.request, _("Password was updated successfully"))

        return result


class ChangeEmailView(FormView):
    template_name = "change-email.html"
    form_class = UpdateEmailForm
    success_url = reverse_lazy("account-change-email")
    model = User

    def form_valid(self, form):
        if self.request.user.is_ngohub_user:
            raise PermissionDenied(_("You cannot change the email for an NGO Hub account"))

        form.instance = self.request.user

        valid = super().form_valid(form)
        if valid:
            form.save()
            messages.success(self.request, _("Email was updated successfully"))

        return valid


class CommissionMemberInviteView(auth_views.PasswordResetView):
    template_name = "invite-commission-member.html"
    form_class = InviteCommissionForm
    success_url = reverse_lazy("admin-invite-commission")
    model = User

    def form_valid(self, form):
        user = self.request.user

        if not user.groups.filter(name__in=[STAFF_GROUP, SUPPORT_GROUP]).exists():
            raise PermissionDenied(_("You are not allowed to invite a commission member"))

        valid = super().form_valid(form)

        if valid:
            messages.success(self.request, _("Commission member was invited successfully"))
        else:
            messages.error(self.request, _("Commission member could not be invited"))

        return valid
