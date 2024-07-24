from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import Group

from accounts.models import User
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.utils.translation import gettext as _

from hub.models import COMMITTEE_GROUP


class UpdateEmailForm(ModelForm):
    class Meta:
        model = User
        fields = ("email",)

    def clean_email(self):
        if User.objects.filter(email=self.cleaned_data.get("email")).exists():
            raise ValidationError(_("This email can't be set."))

        return self.cleaned_data.get("email")

    def save(self, commit=True):
        self.instance.email = self.cleaned_data.get("email")

        return super().save(commit)


class InviteCommissionForm(PasswordResetForm):
    class Meta:
        model = User
        fields = ("email",)

    def clean_email(self):
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

        kwargs["subject_template_name"] = "emails/01_invite_commission_member_subject.txt"
        kwargs["email_template_name"] = "emails/01_invite_commission_member.html"

        super().save(**kwargs)

        return new_user
