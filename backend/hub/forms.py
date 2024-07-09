from django import forms
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_recaptcha.fields import ReCaptchaField

from civil_society_vote.common.messaging import send_email
from hub.models import Candidate, City, Domain, FeatureFlag, Organization

# from django_crispy_bulma.widgets import EmailInput

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
    "organization_head_name",
    "board_council",
    "logo",
    "last_balance_sheet",
    "statute",
    "report_2023",
    "report_2022",
    "report_2021",
    "report_2020",
    "report_2019",
    "report_2018",
    "report_2017",
    "fiscal_certificate_anaf",
    "fiscal_certificate_local",
    "statement_discrimination",
    "statement_political",
    "accept_terms_and_conditions",
]


class OrganizationCreateForm(forms.ModelForm):
    captcha = ReCaptchaField(
        label="",
    )

    field_order = ORG_FIELD_ORDER

    class Meta:
        model = Organization
        exclude = [
            "user",
            "status",
            "status_changed",
            "report_2023",
            "report_2022",
            "report_2021",
            "report_2020",
            "report_2019",
            "report_2018",
            "report_2017",
            "fiscal_certificate_anaf",
            "fiscal_certificate_local",
            "statement_discrimination",
            "statement_political",
            "rejection_message",
        ]
        widgets = {
            "email": forms.widgets.TextInput(),  # EmailInput(),
            "legal_representative_email": forms.widgets.TextInput(),  # EmailInput(),
            "city": forms.Select(attrs={"data-url": reverse_lazy("city-autocomplete")}),
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


class OrganizationUpdateForm(forms.ModelForm):
    field_order = ORG_FIELD_ORDER

    # If the organization is managed through NGO Hub, then these fields should not be editable here
    ngohub_fields = (
        "address",
        "board_council",
        "city",
        "county",
        "description",
        "email",
        "legal_representative_email",
        "legal_representative_name",
        "legal_representative_phone",
        "logo",
        "name",
        "organization_head_name",
        "phone",
        "registration_number",
        "statute",
    )

    class Meta:
        model = Organization
        exclude = [
            "user",
            "status",
            "status_changed",
            "accept_terms_and_conditions",
            "rejection_message",
            "ngohub_org_id",
        ]
        widgets = {
            "email": forms.widgets.TextInput(),  # EmailInput(),
            "legal_representative_email": forms.widgets.TextInput(),  # EmailInput(),
            "city": forms.Select(attrs={"data-url": reverse_lazy("city-autocomplete")}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["city"].queryset = City.objects.filter(county__iexact=self.instance.county)

        if "county" in self.data:
            try:
                self.fields["city"].queryset = City.objects.filter(county__iexact=self.data["county"])
            except (ValueError, TypeError):
                pass  # invalid input, fallback to empty queryset

        if self.instance and not self.instance.is_fully_editable:
            for field_name in self.fields:
                if field_name in self.ngohub_fields:
                    self.fields[field_name].disabled = True
                    # TODO Find a better way to disable the file input widget
                    if type(self.fields[field_name].widget) is forms.widgets.ClearableFileInput:
                        self.fields[field_name].widget = forms.widgets.TextInput()

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if (
            Organization.objects.filter(
                email=email, status__in=[Organization.STATUS.accepted, Organization.STATUS.pending]
            )
            .exclude(user=self.instance.user)
            .exists()
        ):
            raise ValidationError(_("An organization with the same email address is already registered."))
        return self.cleaned_data.get("email")


class CandidateRegisterForm(forms.ModelForm):
    class Meta:
        model = Candidate
        exclude = ["initial_org", "status", "status_changed"]

        widgets = {
            "org": forms.HiddenInput(),
            "is_proposed": forms.HiddenInput(),
            # "email": EmailInput(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

        if not self.user.orgs.exists():
            raise ValidationError(_("Authenticated user does not have an organization."))

        if Candidate.objects_with_org.filter(org=self.user.orgs.first()).exists():
            raise ValidationError(_("Organization already has a candidate."))

        self.initial["org"] = self.user.orgs.first().id

        if FeatureFlag.flag_enabled("single_domain_round"):
            self.fields["domain"].widget.attrs["disabled"] = True
            self.initial["domain"] = Domain.objects.first().id

    def clean_org(self):
        return self.user.orgs.first().id

    def clean_domain(self):
        if FeatureFlag.flag_enabled("single_domain_round"):
            return Domain.objects.first()
        return self.cleaned_data.get("domain")

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get("is_proposed") and not self.user.orgs.first().is_complete:
            raise ValidationError(
                _("To add a candidate you must upload all required documents in 'Organization Profile'")
            )

        if cleaned_data.get("is_proposed") and not self.user.orgs.first().candidate.is_complete:
            raise ValidationError(_("Please add all candidate fields"))

        return cleaned_data


class CandidateUpdateForm(forms.ModelForm):
    field_order = ["name"]

    class Meta:
        model = Candidate
        exclude = ["org", "initial_org", "status", "status_changed"]

        widgets = {
            "is_proposed": forms.HiddenInput(),
            # "email": EmailInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not FeatureFlag.flag_enabled("enable_candidate_registration"):
            for key in self.fields.keys():
                self.fields[key].widget.attrs["disabled"] = True

        if self.instance.is_proposed:
            del self.fields["name"]
            del self.fields["domain"]

            for key in self.fields.keys():
                self.fields[key].widget.attrs["required"] = True

    def save(self, commit=True):
        if not FeatureFlag.flag_enabled("enable_candidate_registration"):
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

    def send_form_email(self):
        send_email(
            subject=f"[VotONG] Contact {self.cleaned_data.get('name')}",
            to_emails=[settings.CONTACT_EMAIL],
            text_template="emails/06_contact.txt",
            html_template="emails/06_contact.html",
            context={
                "name": self.cleaned_data.get("name"),
                "email": self.cleaned_data.get("email"),
                "message": self.cleaned_data.get("message"),
            },
            from_email=settings.NO_REPLY_EMAIL,
        )
