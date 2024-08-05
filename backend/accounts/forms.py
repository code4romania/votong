from django import forms
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.utils.translation import gettext as _

from accounts.models import COMMITTEE_GROUP, User


class CommonEmailConfirmationForm(forms.Form):
    email = forms.EmailField()
    email2 = forms.EmailField()

    def _check_emails_match(self):
        email = self.cleaned_data.get("email")
        email2 = self.cleaned_data.get("email2")

        if email != email2:
            raise ValidationError(_("Emails don't match."))

    def clean_email(self):
        return self.cleaned_data.get("email")

    def clean_email2(self):
        return self.cleaned_data.get("email2")

    def clean(self):
        cleaned_data = super().clean()
        self._check_emails_match()
        return cleaned_data


class UpdateEmailForm(CommonEmailConfirmationForm, ModelForm):
    class Meta:
        model = User
        fields = ("email",)

    def clean_email(self):
        super().clean_email()
        if User.objects.filter(email=self.cleaned_data.get("email")).exists():
            raise ValidationError(_("This email can't be set."))

        return self.cleaned_data.get("email")

    def save(self, commit=True):
        self.instance.email = self.cleaned_data.get("email")

        return super().save(commit)


class InviteCommissionForm(CommonEmailConfirmationForm, PasswordResetForm):
    def clean_email(self):
        super().clean_email()

        if User.objects.filter(email=self.cleaned_data.get("email")).exists():
            raise ValidationError(_("This email can't be set."))

        return self.cleaned_data.get("email")

    def save(self, commit=True, *args, **kwargs):
        email = self.cleaned_data.get("email")

        new_user = User()
        new_user.username = email
        new_user.email = email
        new_user.is_active = True
        new_user.save()

        new_user.groups.add(Group.objects.get(name=COMMITTEE_GROUP))

        kwargs["subject_template_name"] = "accounts/emails/01_invite_commission_member_subject.txt"
        kwargs["html_email_template_name"] = "accounts/emails/01_invite_commission_member.html"
        kwargs["email_template_name"] = "accounts/emails/01_invite_commission_member.txt"
        kwargs["from_email"] = settings.DEFAULT_FROM_EMAIL

        super().save(**kwargs)

        return new_user
