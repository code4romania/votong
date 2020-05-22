from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from django_crispy_bulma.widgets import EmailInput

# from captcha.fields import ReCaptchaField
# from captcha.widgets import ReCaptchaV3

from hub import models


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
