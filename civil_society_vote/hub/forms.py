from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django_crispy_bulma.widgets import EmailInput

from hub import models

# from captcha.fields import ReCaptchaField
# from captcha.widgets import ReCaptchaV3


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = models.Organization
        exclude = ["user", "status", "status_changed"]
        widgets = {
            "email": EmailInput(),
        }


class OrganizationRegisterForm(forms.ModelForm):
    # captcha = ReCaptchaField(widget=ReCaptchaV3(attrs={"required_score": 0.3, "action": "register"}), label="",)

    class Meta:
        model = models.Organization
        exclude = ["user", "status", "status_changed"]
        widgets = {
            "email": EmailInput(),
            "city": forms.Select(attrs={"data-url": reverse_lazy("city-autocomplete"),}),
            # "logo": AdminResubmitImageWidget,
            # "last_balance_sheet": AdminResubmitFileWidget,
            # "statute": AdminResubmitFileWidget,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

    def clean_org(self):
        try:
            org = models.Organization.objects.get(user=self.user)
        except models.Organization.DoesNotExist:
            raise ValidationError(_("Authenticated user does not have an organization."))
        except models.Organization.MultipleObjectsReturned:
            raise ValidationError(_("Authenticated user has more than one organization."))

        if org.candidate:
            raise ValidationError(_("Organization already has a candidate."))

        return org.id


class ImportCitiesForm(forms.Form):
    csv_file = forms.FileField(label=_("CSV file"))

    def clean_csv_file(self):
        f = self.cleaned_data["csv_file"]
        if not f.name.lower().endswith(".csv"):
            raise ValidationError(_("Uploaded file is not a CSV file"))
