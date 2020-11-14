from captcha.fields import ReCaptchaField
from django import forms
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django_crispy_bulma.widgets import EmailInput

from hub.models import Candidate, City, FeatureFlag, Organization

ORG_FIELD_ORDER = [
    "name",
    "county",
    "city",
    "address",
    "registration_number",
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
    "statute",
    "report_2019",
    "report_2018",
    "report_2017",
    "fiscal_certificate",
    "statement",
    "politic_members",
    "accept_terms_and_conditions",
]


class OrganizationCreateForm(forms.ModelForm):
    captcha = ReCaptchaField(label="",)

    field_order = ORG_FIELD_ORDER

    class Meta:
        model = Organization
        exclude = [
            "user",
            "status",
            "status_changed",
            "report_2019",
            "report_2018",
            "report_2017",
            "fiscal_certificate",
            "statement",
            "rejection_message",
        ]
        widgets = {
            "email": EmailInput(),
            "legal_representative_email": EmailInput(),
            "city": forms.Select(attrs={"data-url": reverse_lazy("city-autocomplete"),}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not settings.RECAPTCHA_PUBLIC_KEY:
            del self.fields["captcha"]

        self.fields["city"].queryset = City.objects.none()

        if "city" not in self.data:
            self.fields["city"].widget.attrs.update({"disabled": "true"})

        if "county" in self.data:
            try:
                county = self.data.get("county")
                self.fields["city"].queryset = City.objects.filter(county__iexact=county)
            except (ValueError, TypeError):
                pass  # invalid input, fallback to empty queryset

        self.fields["accept_terms_and_conditions"].required = True
        self.fields["accept_terms_and_conditions"].label = mark_safe(
            _(
                'I agree to the <a href="https://votong.ro/ro/termeni/" target="_blank" rel="noopener noreferrer">Terms and Conditions</a> '
                "of the VotONG platform"
            )
        )

        self.fields["politic_members"].required = True
        self.fields["politic_members"].label = mark_safe(
            _(
                "I declare that the members of the management of the organization I represent (the President and the "
                "members of the Board of Directors) do not occupy leading positions of political parties and are not elected officials."
            )
        )

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if Organization.objects.filter(
            email=email, status__in=[Organization.STATUS.accepted, Organization.STATUS.pending]
        ).exists():
            raise ValidationError(_("An organization with the same email address is already registered."))
        return self.cleaned_data.get("email")

    def clean_accept_terms_and_conditions(self):
        if not self.cleaned_data.get("accept_terms_and_conditions"):
            raise ValidationError(_("You need to accept terms and conditions."))
        return self.cleaned_data.get("accept_terms_and_conditions")

    def clean_politic_members(self):
        if not self.cleaned_data.get("politic_members"):
            raise ValidationError(_("Organisation members need to be apolitical."))
        return self.cleaned_data.get("politic_members")


class OrganizationUpdateForm(forms.ModelForm):
    field_order = ORG_FIELD_ORDER

    class Meta:
        model = Organization
        exclude = ["user", "status", "status_changed", "accept_terms_and_conditions", "rejection_message"]
        widgets = {
            "email": EmailInput(),
            "legal_representative_email": EmailInput(),
            "city": forms.Select(attrs={"data-url": reverse_lazy("city-autocomplete"),}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["city"].queryset = City.objects.filter(county__iexact=self.instance.county)

        if "county" in self.data:
            try:
                self.fields["city"].queryset = City.objects.filter(county__iexact=self.data["county"])
            except (ValueError, TypeError):
                pass  # invalid input, fallback to empty queryset

        self.fields["politic_members"].required = True
        self.fields["politic_members"].label = mark_safe(
            _(
                "I declare that the members of the management of the organization I represent (the President and the "
                "members of the Board of Directors) do not occupy leading positions of political parties and are not elected officials."
            )
        )

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if Organization.objects.filter(
            email=email, status__in=[Organization.STATUS.accepted, Organization.STATUS.pending]
        ).exists():
            raise ValidationError(_("An organization with the same email address is already registered."))
        return self.cleaned_data.get("email")

    def clean_politic_members(self):
        if not self.cleaned_data.get("politic_members"):
            raise ValidationError(_("Organisation members need to be apolitical."))
        return self.cleaned_data.get("politic_members")


class CandidateRegisterForm(forms.ModelForm):
    class Meta:
        model = Candidate
        exclude = ["initial_org", "status", "status_changed"]

        widgets = {
            "org": forms.HiddenInput(),
            "is_proposed": forms.HiddenInput(),
            "email": EmailInput(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

        if not self.user.orgs.exists():
            raise ValidationError(_("Authenticated user does not have an organization."))

        if Candidate.objects_with_org.filter(org=self.user.orgs.first()).exists():
            raise ValidationError(_("Organization already has a candidate."))

        self.initial["org"] = self.user.orgs.first().id

    def clean_org(self):
        return self.user.orgs.first().id

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get("is_proposed") and not self.user.orgs.first().is_complete:
            raise ValidationError(
                _("To add a candidate you must upload all required documents in 'Organization Profile'")
            )

        return cleaned_data


class CandidateUpdateForm(forms.ModelForm):
    field_order = ["name"]

    class Meta:
        model = Candidate
        exclude = ["org", "initial_org", "status", "status_changed"]

        widgets = {
            "is_proposed": forms.HiddenInput(),
            "email": EmailInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not FeatureFlag.objects.filter(flag="enable_candidate_registration", is_enabled=True).exists():
            for key in self.fields.keys():
                self.fields[key].widget.attrs["disabled"] = True

        if self.instance.is_proposed:
            del self.fields["name"]

    def save(self, commit=True):
        if not FeatureFlag.objects.filter(flag="enable_candidate_registration", is_enabled=True).exists():
            # This should not happen unless someone messes with the form code
            raise PermissionDenied

        candidate = Candidate.objects_with_org.get(pk=self.instance.id)

        if candidate.is_proposed and not self.cleaned_data.get("is_proposed"):
            if commit:
                # This should not happen unless someone messes with the form code
                raise ValidationError(_("[ERROR 32202] Please contact the site administrator."))

        return super().save(commit)


class ImportCitiesForm(forms.Form):
    csv_file = forms.FileField(label=_("CSV file"))

    def clean_csv_file(self):
        f = self.cleaned_data["csv_file"]
        if not f.name.lower().endswith(".csv"):
            raise ValidationError(_("Uploaded file is not a CSV file"))


class ContactForm(forms.Form):
    name = forms.CharField(required=True)
    email = forms.CharField(required=True)
    message = forms.CharField(required=True)
    terms_and_conditions = forms.BooleanField(required=True)

    captcha = ReCaptchaField(label="")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not settings.RECAPTCHA_PUBLIC_KEY:
            del self.fields["captcha"]

    def send_email(self):
        send_mail(
            f"Contact {self.cleaned_data.get('name')}",
            f"{self.cleaned_data.get('email')}: {self.cleaned_data.get('message')}",
            settings.NO_REPLY_EMAIL,
            (settings.DEFAULT_FROM_EMAIL,),
        )
