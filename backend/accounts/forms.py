from accounts.models import User
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.utils.translation import gettext as _


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
