from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV3
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django_crispy_bulma.widgets import EmailInput

from hub import models


class OrganizationForm(forms.ModelForm):
    captcha = ReCaptchaField(widget=ReCaptchaV3(attrs={"required_score": 0.3, "action": "register"}), label="",)

    field_order = [
        "name",
        "county",
        "city",
        "address",
        "email",
        "phone",
        "description",
        "legal_representative_name",
        "legal_representative_email",
        "legal_representative_phone",
        "organisation_head_name",
        "board_council",
        "logo",
        "last_balance_sheet",
        "statute"
    ]

    class Meta:
        model = models.Organization
        exclude = ["user", "status", "status_changed"]
        widgets = {
            "email": EmailInput(),
            "legal_representative_email": EmailInput(),
            "city": forms.Select(attrs={"data-url": reverse_lazy("city-autocomplete"),}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not settings.RECAPTCHA_PUBLIC_KEY:
            del self.fields["captcha"]

        self.fields["city"].queryset = models.City.objects.none()

        if "city" not in self.data:
            self.fields["city"].widget.attrs.update({"disabled": "true"})

        if "county" in self.data:
            try:
                county = self.data.get("county")
                self.fields["city"].queryset = models.City.objects.filter(county__iexact=county)
            except (ValueError, TypeError):
                pass  # invalid input, fallback to empty queryset


class CandidateRegisterForm(forms.ModelForm):
    class Meta:
        model = models.Candidate
        fields = "__all__"

        widgets = {
            "org": forms.HiddenInput(),
            "email": EmailInput(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

        if not self.user.orgs.exists():
            raise ValidationError(_("Authenticated user does not have an organization."))

        if models.Candidate.objects.filter(org=self.user.orgs.first()).exists():
            raise ValidationError(_("Organization already has a candidate."))

        self.initial["org"] = self.user.orgs.first().id

    def clean_org(self):
        return self.user.orgs.first().id


class CandidateUpdateForm(forms.ModelForm):
    class Meta:
        model = models.Candidate
        fields = "__all__"
        exclude = ["org"]

        widgets = {
            "email": EmailInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ImportCitiesForm(forms.Form):
    csv_file = forms.FileField(label=_("CSV file"))

    def clean_csv_file(self):
        f = self.cleaned_data["csv_file"]
        if not f.name.lower().endswith(".csv"):
            raise ValidationError(_("Uploaded file is not a CSV file"))
