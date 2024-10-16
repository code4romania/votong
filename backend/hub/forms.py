from typing import Dict, List

from django import forms
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_recaptcha.fields import ReCaptchaField

from civil_society_vote.common.messaging import send_email
from hub.models import Candidate, City, Domain, FLAG_CHOICES, FeatureFlag, Organization


ORG_FIELD_ORDER = [
    "name",
    "county",
    "city",
    "address",
    "registration_number",
    "email",
    "phone",
    "description",
    "voting_domain",
    "legal_representative_name",
    "legal_representative_email",
    "legal_representative_phone",
    "board_council",
    "logo",
    "last_balance_sheet",
    "statute",
    "statement_political",
    "report_2023",
    "report_2022",
    "report_2021",
    "fiscal_certificate_anaf",
    "fiscal_certificate_local",
    "statement_discrimination",
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

        if not self.instance:
            return

        self._set_fields_permissions()

    def _set_fields_permissions(self):
        if self.instance:
            if FeatureFlag.flag_enabled(FLAG_CHOICES.enable_voting_domain):
                self.fields["voting_domain"].disabled = self.instance.voting_domain is not None
            else:
                del self.fields["voting_domain"]

        # All the required fields for a fully editable organization should be required in votong
        if self.instance.is_fully_editable:
            for field_name in self.fields:
                if field_name in Organization.required_fields():
                    self.fields[field_name].required = True

            return

        # If registration is closed, updating the organization/candidate shouldn't be possible
        if not FeatureFlag.flag_enabled(FLAG_CHOICES.enable_candidate_registration):
            for field_name in self.fields:
                self.fields[field_name].disabled = True

            if "voting_domain" in self.fields:
                self.fields["voting_domain"].disabled = self.instance.voting_domain is not None

            return

        # Disable the fields that should be received from NGO Hub
        for field_name in self.fields:
            if field_name in Organization.ngohub_fields():
                self.fields[field_name].disabled = True

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

    def clean_voting_domain(self):
        if not FeatureFlag.flag_enabled(FLAG_CHOICES.enable_voting_domain):
            return None

        new_voting_domain = self.cleaned_data.get("voting_domain")
        if (
            self.instance
            and self.instance.voting_domain is not None
            and new_voting_domain != self.instance.voting_domain
        ):
            raise ValidationError(_("Voting domain cannot be changed. Please contact the site administrator."))

        return new_voting_domain

    def save(self, commit=True):
        if not FeatureFlag.flag_enabled(FLAG_CHOICES.enable_candidate_registration):
            # This should not happen unless someone messes with the form code
            raise PermissionDenied

        return super().save(commit)


class CandidateCommonForm(forms.ModelForm):
    field_order = [
        "domain",
        "name",
        "role",
        "photo",
        "statement",
        "mandate",
        "letter_of_intent",
        "cv",
        "declaration_of_interests",
        "fiscal_record",
        "criminal_record",
    ]

    class Meta:
        model = Candidate

        exclude: List[str] = ["initial_org", "status", "status_changed"]

        widgets: Dict = {
            "is_proposed": forms.HiddenInput(),
        }


class CandidateRegisterForm(CandidateCommonForm):

    class Meta(CandidateCommonForm.Meta):
        widgets = {
            "is_proposed": forms.HiddenInput(),
            "org": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

        if not self.user.orgs.exists():
            raise ValidationError(_("Authenticated user does not have an organization."))

        user_org: Organization = self.user.orgs.first()
        if Candidate.objects_with_org.filter(org=user_org).exists():
            raise ValidationError(_("Organization already has a candidate."))

        self.initial["org"] = user_org.id

        if FeatureFlag.flag_enabled(FLAG_CHOICES.single_domain_round):
            self.fields["domain"].widget.attrs["disabled"] = True
            self.initial["domain"] = Domain.objects.first().id

        if FeatureFlag.flag_enabled(FLAG_CHOICES.enable_voting_domain):
            self.fields["domain"].widget.attrs["disabled"] = True
            self.initial["domain"] = user_org.voting_domain

    def clean_org(self):
        return self.user.orgs.first().id

    def clean_domain(self):
        if FeatureFlag.flag_enabled(FLAG_CHOICES.single_domain_round):
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


class CandidateUpdateForm(CandidateCommonForm):

    class Meta(CandidateCommonForm.Meta):
        exclude: List[str] = ["org", "initial_org", "status", "status_changed"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not FeatureFlag.flag_enabled(FLAG_CHOICES.enable_candidate_registration):
            for key in self.fields.keys():
                self.fields[key].widget.attrs["disabled"] = True

        if self.instance.is_proposed:
            del self.fields["name"]
            del self.fields["domain"]

            for key in self.fields.keys():
                self.fields[key].widget.attrs["required"] = True

        # If registration is closed, updating the organization/candidate shouldn't be possible
        if not FeatureFlag.flag_enabled(FLAG_CHOICES.enable_candidate_registration):
            for field_name in self.fields:
                self.fields[field_name].disabled = True

    def save(self, commit=True):
        if not FeatureFlag.flag_enabled(FLAG_CHOICES.enable_candidate_registration):
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
            text_template="hub/emails/06_contact.txt",
            html_template="hub/emails/06_contact.html",
            context={
                "name": self.cleaned_data.get("name"),
                "email": self.cleaned_data.get("email"),
                "message": self.cleaned_data.get("message"),
            },
            from_email=settings.NO_REPLY_EMAIL,
        )
