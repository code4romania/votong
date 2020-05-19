from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from django_crispy_bulma.widgets import EmailInput
from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV3

from hub import models


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = models.Organization
        fields = "__all__"


class OrganizationRegisterRequestForm(forms.ModelForm):
    captcha = ReCaptchaField(widget=ReCaptchaV3(attrs={"required_score": 0.3, "action": "register"}), label="",)

    class Meta:
        model = models.Organization
        fields = [
            "name",
            "county",
            "city",
            "address",
            "email",
            "representative",
            "phone",
            "logo",
            "last_balance_sheet",
            "statute",
        ]
        widgets = {
            "email": EmailInput(),
            # "logo": AdminResubmitImageWidget,
            # "last_balance_sheet": AdminResubmitFileWidget,
            # "statute": AdminResubmitFileWidget,
        }


class OrganizationVoteForm(forms.ModelForm):
    class Meta:
        model = models.OrganizationVote
        fields = ("vote", "motivation")


class ImportCitiesForm(forms.Form):
    csv_file = forms.FileField(label=_("CSV file"))

    def clean_csv_file(self):
        f = self.cleaned_data["csv_file"]
        if not f.name.lower().endswith(".csv"):
            raise ValidationError(_("Uploaded file is not a CSV file"))
