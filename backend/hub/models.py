import logging
from typing import List, Set

from auditlog.registry import auditlog
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.storage import storages
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models.query_utils import DeferredAttribute
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from guardian.shortcuts import assign_perm
from model_utils import Choices
from model_utils.models import StatusModel, TimeStampedModel
from tinymce.models import HTMLField

from accounts.models import COMMITTEE_GROUP, COMMITTEE_GROUP_READ_ONLY, NGO_GROUP, STAFF_GROUP, SUPPORT_GROUP, User
from civil_society_vote.common.cache import cache_decorator, delete_cache_key
from civil_society_vote.common.formatting import get_human_readable_size

REPORTS_HELP_TEXT = (
    "Rapoartele anuale trebuie să includă sursele de finanțare din care să rezulte că organizația dispune de resurse "
    "financiare şi umane pentru îndeplinirea mandatului de membru în Comisia Electorală a VotONG."
)

logger = logging.getLogger(__name__)


def file_validator(file):
    if file.size > settings.MAX_DOCUMENT_SIZE:
        human_readable_size = get_human_readable_size(file.size)
        raise ValidationError(
            _(
                "The file size is %(actual_size)d %(actual_unit)s "
                "but it must be under %(expected_size)d %(expected_unit)s"
            )
            % (
                human_readable_size["size"],
                human_readable_size["unit"],
                settings.MAX_DOCUMENT_SIZE_IN_UNIT,
                settings.MAX_DOCUMENT_SIZE_UNIT,
            )
        )


def select_public_storage():
    return storages["public"]


UserModel = get_user_model()

COUNTY_RESIDENCE = [
    ("Alba", "Alba Iulia"),
    ("Arad", "Arad"),
    ("Arges", "Pitesti"),
    ("Bacau", "Bacau"),
    ("Bihor", "Oradea"),
    ("Bistrita-Nasaud", "Bistrita"),
    ("Botosani", "Botosani"),
    ("Braila", "Braila"),
    ("Brasov", "Brasov"),
    ("Bucuresti", "Bucuresti"),
    ("Buzau", "Buzau"),
    ("Caras-Severin", "Resita"),
    ("Calarasi", "Calarasi"),
    ("Cluj", "Cluj-Napoca"),
    ("Constanta", "Constanta"),
    ("Covasna", "Sfantu Gheorghe"),
    ("Dambovita", "Targoviste"),
    ("Dolj", "Craiova"),
    ("Galati", "Galati"),
    ("Giurgiu", "Giurgiu"),
    ("Gorj", "Targu Jiu"),
    ("Harghita", "Miercurea Ciuc"),
    ("Hunedoara", "Deva"),
    ("Ialomita", "Slobozia"),
    ("Iasi", "Iasi"),
    ("Ilfov", "Buftea"),
    ("Maramures", "Baia Mare"),
    ("Mehedinti", "Drobeta-Turnu Severin"),
    ("Mures", "Targu Mures"),
    ("Neamt", "Piatra Neamt"),
    ("Olt", "Slatina"),
    ("Prahova", "Ploiesti"),
    ("Satu Mare", "Satu Mare"),
    ("Salaj", "Zalau"),
    ("Sibiu", "Sibiu"),
    ("Suceava", "Suceava"),
    ("Teleorman", "Alexandria"),
    ("Timis", "Timisoara"),
    ("Tulcea", "Tulcea"),
    ("Vaslui", "Vaslui"),
    ("Valcea", "Ramnicu Valcea"),
    ("Vrancea", "Focsani"),
]
COUNTIES = [x[0] for x in COUNTY_RESIDENCE]

COUNTY_CHOICES = Choices(*[(x, x) for x in COUNTIES])

STATE_CHOICES = Choices(
    ("active", _("Active")),
    ("inactive", _("Inactive")),
)

PHASE_CHOICES = Choices(
    ("enable_org_registration", _("Enable organization registration")),
    ("enable_org_editing", _("Enable organization editing")),
    ("enable_org_approval", _("Enable organization approvals")),
    ("enable_candidate_registration", _("Enable candidate registration")),
    ("enable_candidate_editing", _("Enable candidate editing")),
    ("enable_candidate_supporting", _("Enable candidate supporting")),
    ("enable_candidate_voting", _("Enable candidate voting")),
    ("enable_candidate_confirmation", _("Enable candidate confirmation")),
    ("enable_pending_results", _("Enable the phase when waiting for the display of results")),
    ("enable_results_display", _("Enable the display of results")),
    ("enable_final_results_display", _("Enable the display of results after resolving all complaints")),
)
SETTINGS_CHOICES = Choices(
    ("single_domain_round", _("Voting round with just one domain (some restrictions will apply)")),
    ("global_support_round", _("Enable global support (the support of at least 10 organizations is required)")),
    ("enable_voting_domain", _("Enable the voting domain restriction for an organization")),
)
FLAG_CHOICES = PHASE_CHOICES + SETTINGS_CHOICES


def get_feature_flag(flag_choice: str) -> bool:
    if not flag_choice or flag_choice not in FLAG_CHOICES:
        raise ValueError(f"Invalid flag choice: {flag_choice}. Valid choices are: {FLAG_CHOICES}")

    try:
        feature_flag_status: bool = FeatureFlag.objects.get(flag=flag_choice).is_enabled
    except FeatureFlag.DoesNotExist:
        return False

    return feature_flag_status


class FeatureFlag(TimeStampedModel):
    flag = models.CharField(_("Flag"), choices=FLAG_CHOICES, max_length=254, unique=True)
    is_enabled = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Feature flag")
        verbose_name_plural = _("Feature flags")

    def __str__(self):
        return f"{FLAG_CHOICES[self.flag]}"

    @staticmethod
    def delete_cache():
        delete_cache_key("feature_flags")

    @staticmethod
    @cache_decorator(cache_key="feature_flags", timeout=settings.TIMEOUT_CACHE_SHORT)
    def get_feature_flags():
        return {flag.flag: flag.is_enabled for flag in FeatureFlag.objects.all()}

    @staticmethod
    def flag_enabled(flag: str) -> bool:
        """
        Check if the requested feature flag is enabled
        """
        if not flag:
            return False

        return FeatureFlag.get_feature_flags().get(flag, False)


class BlogPost(TimeStampedModel):
    title = models.CharField(_("Title"), max_length=254)
    slug = models.SlugField(unique=True)
    author = models.CharField(_("Author"), max_length=100)
    content_preview = models.TextField(_("Content preview"))
    content = HTMLField(
        _("Content"),
    )
    is_visible = models.BooleanField(_("Is visible?"), default=False)
    published_date = models.DateField(_("Date published"), blank=True, null=True)

    class Meta:
        verbose_name = _("Blog post")
        verbose_name_plural = _("Blog posts")

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("blog-post", args=[self.slug])

    def __str__(self):
        return self.title


class Domain(TimeStampedModel):
    name = models.CharField(_("Name"), max_length=254, unique=True)
    description = models.TextField(_("Description"))
    seats = models.PositiveSmallIntegerField(
        _("Number of seats"),
        default=0,
        help_text="Numărul de locuri disponibile într-un domeniu este egal cu numărul de voturi pe are un elector le poate exprima în acel domeniu. Setând numărul de locuri se setează și numărul maxim de voturi.",
    )

    class Meta:
        verbose_name = _("Domain")
        verbose_name_plural = _("Domains")

    def __str__(self):
        return self.name

    def accepted_candidates(self):
        return (
            self.candidates.filter(status=Candidate.STATUS.accepted, is_proposed=True)
            .annotate(votes_count=models.Count("votes", distinct=True))
            .order_by("-votes_count")
        )

    def confirmed_candidates(self):
        return (
            self.candidates.filter(status=Candidate.STATUS.confirmed, is_proposed=True)
            .annotate(votes_count=models.Count("votes", distinct=True))
            .order_by("-votes_count")
        )


class City(models.Model):
    city = models.CharField(_("City"), max_length=100)
    county = models.CharField(_("County"), max_length=50)
    is_county_residence = models.BooleanField(_("Is county residence"), default=False)

    class Meta:
        verbose_name = _("City")
        verbose_name_plural = _("Cities")
        unique_together = ["city", "county"]

    def __str__(self):
        return f"{self.city} ({self.county})"

    def save(self, *args, **kwargs):
        self.is_county_residence = False
        if (self.county, self.city) in COUNTY_RESIDENCE:
            self.is_county_residence = True

        super().save(*args, **kwargs)


class BaseCompleteModel(models.Model):
    class Meta:
        abstract = True

    @classmethod
    def required_fields(cls) -> List[DeferredAttribute]:
        raise NotImplementedError

    def check_deferred_fields(self, deferred_required_fields):
        missing_fields = []

        for field in deferred_required_fields:
            if not getattr(self, field.field.name):
                missing_fields.append(field.field)

        return missing_fields

    def get_missing_fields(self):
        deferred_required_fields = self.required_fields()
        missing_fields = self.check_deferred_fields(deferred_required_fields)

        return missing_fields

    @property
    def is_complete(self):
        missing_fields = self.get_missing_fields()

        return not missing_fields


class BaseOrganizationManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(status=Organization.STATUS.draft)


class BaseOrganizationElectorManager(BaseOrganizationManager):
    def get_queryset(self):
        return super().get_queryset().exclude(status=Organization.STATUS.admin)


class OrganizationAdminManager(BaseOrganizationManager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Organization.STATUS.admin)


class OrganizationAcceptedManager(BaseOrganizationElectorManager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Organization.STATUS.accepted)


class Organization(StatusModel, TimeStampedModel, BaseCompleteModel):
    # DRAFT: empty organization created by us, it might be invalid (e.g., created for another user of an org
    # PENDING: the organization doesn't have all the necessary documents
    # ACCEPTED: the organization has all required documentation and can vote
    # REJECTED: the organization was rejected by the electoral commission
    STATUS = Choices(
        ("draft", _("Draft")),
        ("pending", _("Pending approval")),
        ("ngohub_accepted", _("NGO Hub accepted")),
        ("accepted", _("Accepted")),
        ("admin", _("Admin")),
        ("rejected", _("Rejected")),
    )
    status = models.CharField(_("Status"), choices=STATUS, default=STATUS.draft, max_length=30, db_index=True)

    ngohub_org_id = models.PositiveBigIntegerField(_("NGO Hub linked organization ID"), default=0, db_index=True)

    voting_domain = models.ForeignKey(
        Domain,
        verbose_name=_("Voting domain"),
        on_delete=models.PROTECT,
        related_name="organizations",
        null=True,
        blank=True,
        help_text=_(
            "The domain in which the organization can vote, support, and propose candidates"
            " – once set, the field can only be modified by the platform's administrators."
        ),
    )

    name = models.CharField(_("NGO Name"), max_length=254, blank=True, default="")
    county = models.CharField(_("County"), max_length=50, blank=True, default="")
    city = models.ForeignKey("City", verbose_name=_("City"), on_delete=models.PROTECT, null=True, blank=True)
    address = models.CharField(_("Address"), max_length=254, blank=True, default="")
    registration_number = models.CharField(_("Registration number"), max_length=20, blank=True, default="")

    email = models.EmailField(_("Organization Email"), blank=True, default="")
    phone = models.CharField(_("Organization Phone"), max_length=30, blank=True, default="")
    description = models.TextField(_("Short Description"), blank=True, default="")

    legal_representative_name = models.CharField(_("Legal Representative Name"), max_length=254, blank=True, default="")
    legal_representative_email = models.EmailField(_("Legal Representative Email"), blank=True, default="")
    legal_representative_phone = models.CharField(
        _("Legal Representative Phone"), max_length=30, blank=True, default=""
    )

    # organization_head_name = models.CharField(_("Organization Head Name"), max_length=254, blank=True, default="")
    board_council = models.CharField(_("Board council"), max_length=1000, blank=True, default="")

    logo = models.FileField(
        _("Logo"),
        max_length=300,
        storage=select_public_storage,
        blank=True,
        default="",
    )
    last_balance_sheet = models.FileField(
        _("First page of last balance sheet for %(CURRENT_EDITION_YEAR)s")
        % {"CURRENT_EDITION_YEAR": str(settings.CURRENT_EDITION_YEAR - 1)},
        blank=True,
        default="",
        max_length=300,
    )
    statute = models.FileField(
        _("NGO Statute"),
        blank=True,
        default="",
        max_length=300,
        help_text="Copie a ultimului statut autentificat al organizației și a hotărârii judecătorești corespunzătoare, definitivă şi irevocabilă și copii ale tuturor documentelor ulterioare/suplimentare ale statutului, inclusiv hotărârile judecătorești definitive și irevocabile; Vă rugăm să arhivați documentele și să încărcați o singură arhivă în platformă.",
    )

    activity_summary = models.TextField(
        _("Current year activity summary"),
        blank=True,
        default="",
        max_length=2000,
        help_text=_(
            "Summary of the activities carried out by the organization in the current year (between 500 and 2000 characters)"
        ),
        validators=[MinLengthValidator(500)],
    )

    report_2023 = models.FileField(
        _("Yearly report 2023"),
        blank=True,
        default="",
        max_length=300,
        help_text=REPORTS_HELP_TEXT,
        validators=[file_validator],
    )
    report_2022 = models.FileField(
        _("Yearly report 2022"),
        blank=True,
        default="",
        max_length=300,
        help_text=REPORTS_HELP_TEXT,
        validators=[file_validator],
    )
    report_2021 = models.FileField(
        _("Yearly report 2021"),
        blank=True,
        default="",
        max_length=300,
        help_text=REPORTS_HELP_TEXT,
        validators=[file_validator],
    )

    statement_discrimination = models.FileField(
        _("Non-discrimination statement"),
        blank=True,
        default="",
        max_length=300,
        help_text="Declarație pe proprie răspundere prin care declară că nu realizează activități sau susține cauze de natură politică sau care discriminează pe considerente legate de etnie, rasă, sex, orientare sexuală, religie, capacități fizice sau psihice sau de apartenența la una sau mai multe categorii sociale sau economice.",
        validators=[file_validator],
    )
    statement_political = models.FileField(
        _("Non-political statement"),
        blank=True,
        default="",
        max_length=300,
        help_text="Declarație pe propria răspundere prin care declar că ONG-ul nu are între membrii conducerii organizației (Președinte sau Consiliul Director) membri ai conducerii unui partid politic sau persoane care au fost alese într-o funcție publică.",
        validators=[file_validator],
    )

    fiscal_certificate_anaf = models.FileField(
        _("Fiscal certificate ANAF"),
        blank=True,
        default="",
        max_length=300,
        help_text="Certificat fiscal emis de ANAF",
        validators=[file_validator],
    )
    fiscal_certificate_local = models.FileField(
        _("Fiscal certificate local"),
        blank=True,
        default="",
        max_length=300,
        help_text="Certificat fiscal emis de Direcția de Impozite și Taxe Locale",
        validators=[file_validator],
    )

    accept_terms_and_conditions = models.BooleanField(_("Accepted Terms and Conditions"), default=False)

    rejection_message = models.TextField(_("Rejection message"), blank=True)

    filename_cache = models.JSONField(_("Filename cache"), editable=False, default=dict, blank=False, null=False)

    ngohub_last_update_started = models.DateTimeField(_("Last NGO Hub update"), null=True, blank=True, editable=False)
    ngohub_last_update_ended = models.DateTimeField(_("Last NGO Hub update"), null=True, blank=True, editable=False)

    objects = models.Manager()
    admin = OrganizationAdminManager()
    accepted = OrganizationAcceptedManager()

    class Meta:
        verbose_name_plural = _("Organizations")
        verbose_name = _("Organization")
        ordering = ["name"]

        permissions = (
            ("view_data_organization", "View data organization"),
            ("approve_organization", "Approve organization"),
        )

    def __str__(self):
        return self.name

    @property
    def get_logo_url(self):
        if self.logo:
            return self.logo.url
        else:
            return ""

    @property
    def is_fully_editable(self):
        """
        Organizations managed elsewhere (ie: on NGO Hub) should not be fully editable here
        """
        if self.ngohub_org_id:
            return False
        return True

    @staticmethod
    def get_required_reports() -> List[str]:
        required_reports = []
        start_year = settings.CURRENT_EDITION_YEAR - settings.PREV_REPORTS_REQUIRED_FOR_PROPOSAL

        for year in range(start_year, settings.CURRENT_EDITION_YEAR):
            required_reports.append(f"report_{year}")

        return required_reports

    @classmethod
    def required_fields(cls) -> List[DeferredAttribute]:
        fields = [
            cls.name,
            cls.county,
            cls.city,
            cls.address,
            cls.registration_number,
            cls.email,
            cls.phone,
            cls.description,
            cls.legal_representative_name,
            cls.legal_representative_email,
            cls.board_council,
            cls.last_balance_sheet,
            cls.statute,
            cls.statement_political,
        ]

        if FeatureFlag.flag_enabled(FLAG_CHOICES.enable_voting_domain):
            fields.append(cls.voting_domain)

        return fields

    @classmethod
    def required_fields_for_candidate(cls) -> List[DeferredAttribute]:
        fields = cls.required_fields()

        # noinspection PyTypeChecker
        fields.extend(
            [
                cls.statement_discrimination,
                cls.fiscal_certificate_anaf,
                cls.fiscal_certificate_local,
                cls.activity_summary,
            ]
        )

        for report_name in cls.get_required_reports():
            fields.append(getattr(cls, report_name))

        return fields

    @staticmethod
    def ngohub_fields():
        # If the organization is managed through NGO Hub, then these fields should not be editable here
        return (
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
            "phone",
            "registration_number",
            "statute",
            "statement_political",
            "last_balance_sheet",
        )

    @staticmethod
    def file_fields(*, include_ngohub=True) -> List[str]:
        file_fields: Set[str] = {
            "logo",
            "last_balance_sheet",
            "statute",
            "report_2023",
            "report_2022",
            "report_2021",
            "statement_discrimination",
            "statement_political",
            "fiscal_certificate_anaf",
            "fiscal_certificate_local",
        }
        if include_ngohub:
            return list(file_fields)

        return list(file_fields - set(Organization.ngohub_fields()))

    def get_missing_fields_for_candidate(self):
        deferred_required_fields = self.required_fields_for_candidate()
        missing_fields = self.check_deferred_fields(deferred_required_fields)

        return missing_fields

    @property
    def is_complete(self):
        """
        Validate that the Org uploaded all the requested info to propose a Candidate
        """
        if not super().is_complete:
            return False

        required_reports_names = self.get_required_reports()
        required_reports = [getattr(self, report_name, None) for report_name in required_reports_names]

        return all(
            [
                self.statute,
                self.last_balance_sheet,
                self.statement_discrimination,
                self.statement_political,
                self.fiscal_certificate_anaf,
                self.fiscal_certificate_local,
            ]
            + required_reports
        )

    @property
    def is_complete_for_candidate(self):
        """
        Validate that the Org uploaded all the requested info to propose a Candidate
        """
        if not super().is_complete:
            return False

        missing_fields = self.get_missing_fields_for_candidate()

        return not missing_fields

    def is_elector(self, domain=None) -> bool:
        if self.status != self.STATUS.accepted:
            return False

        if not FeatureFlag.flag_enabled("enable_voting_domain"):
            return True

        if not domain:
            return False

        return self.voting_domain == domain

    def get_absolute_url(self):
        return reverse("ngo-detail", args=[self.pk])

    def _remove_votes_supports_candidates(self):
        if FeatureFlag.flag_enabled(PHASE_CHOICES.enable_candidate_supporting):
            # Remove votes for candidates that are not in the voting domain
            # This should be done only if we're in the registering and supporting phase
            for candidate in self.candidates.all():
                if candidate.is_proposed:
                    candidate.delete()

            # Remove support that the organization has given
            for supporter in CandidateSupporter.objects.filter(user__organization=self):
                supporter.delete()

        if FeatureFlag.flag_enabled(PHASE_CHOICES.enable_candidate_voting):
            # Remove votes that the organization has given
            for vote in CandidateVote.objects.filter(organization=self):
                vote.delete()

    def _change_candidates_domain(self, voting_domain):
        if hasattr(self, "candidate") and self.candidate:
            self.candidate.old_domain = self.candidate.domain
            self.candidate.domain = voting_domain

            self.candidate.save()

    def save(self, *args, **kwargs):
        create = False if self.id else True

        if self.pk and self.status == self.STATUS.accepted and FeatureFlag.flag_enabled("enable_voting_domain"):
            old_voting_domain = Organization.objects.filter(pk=self.pk).values_list("voting_domain", flat=True).first()
            if old_voting_domain and (not self.voting_domain or self.voting_domain.pk != old_voting_domain):
                self._remove_votes_supports_candidates()
                self._change_candidates_domain(self.voting_domain)

        if self.city:
            self.county = self.city.county
        else:
            self.county = ""

        if self.status == self.STATUS.ngohub_accepted and self.voting_domain:
            self.status = self.STATUS.accepted

        if self.status == self.STATUS.accepted and not self.users.exists():
            self.create_owner()

        super().save(*args, **kwargs)

        if FeatureFlag.flag_enabled(FLAG_CHOICES.enable_voting_domain):
            Candidate.objects.filter(org=self).update(domain=self.voting_domain)

        if self.users:
            user: UserModel
            for user in self.users.all():
                if self.status == self.STATUS.admin:
                    user.make_staff()

                assign_perm("view_data_organization", user, self)
                assign_perm("view_organization", user, self)
                assign_perm("change_organization", user, self)

        if create:
            assign_perm("view_data_organization", Group.objects.get(name=STAFF_GROUP), self)
            assign_perm("view_data_organization", Group.objects.get(name=SUPPORT_GROUP), self)
            assign_perm("view_data_organization", Group.objects.get(name=COMMITTEE_GROUP), self)
            assign_perm("view_data_organization", Group.objects.get(name=COMMITTEE_GROUP_READ_ONLY), self)

            assign_perm("approve_organization", Group.objects.get(name=COMMITTEE_GROUP), self)

    def create_owner(self):
        user = User()

        user.username = self.email
        user.email = self.email
        user.set_password(get_random_string(10))
        user.is_active = True
        user.organization = self

        user.save()

        # Add organization user to the NGO group
        user.groups.add(Group.objects.get(name=NGO_GROUP))

        return user


class CandidatesWithOrgManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(org=None).exclude(org__status=Organization.STATUS.draft)


class CandidatesProposedManager(CandidatesWithOrgManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_proposed=True)


class Candidate(StatusModel, TimeStampedModel, BaseCompleteModel):
    # PENDING: has been created/proposed and is waiting for support from organizations
    # IN_VALIDATION: has been accepted by the admins of the platform and is waiting to be confirmed by the commission
    # CONFIRMED: has received confirmation from the electoral commission
    # REJECTED: has been rejected
    STATUS = Choices(
        ("pending", _("Pending candidate")),
        ("accepted", _("Accepted candidate")),
        ("confirmed", _("Validated candidate")),
        ("rejected", _("Rejected candidate")),
    )
    status = models.CharField(_("Status"), choices=STATUS, default=STATUS.pending, max_length=30, db_index=True)

    org = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name="candidate", null=True, blank=True)
    initial_org = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        related_name="candidates",
        null=True,
        blank=True,
        help_text=_(
            "If this is set, the `org` field will be unset "
            "and the candidate is removed as the official proposal of the organization."
        ),
    )
    domain = models.ForeignKey(
        "Domain",
        verbose_name=_("Domain"),
        on_delete=models.PROTECT,
        related_name="candidates",
        null=True,
        blank=True,
        help_text=_("The domain in which the candidate is running."),
    )
    old_domain = models.ForeignKey(
        "Domain",
        verbose_name=_("Old Domain"),
        on_delete=models.PROTECT,
        related_name="candidates_old",
        null=True,
        blank=True,
        help_text=_("The domain in which the candidate is running."),
    )

    is_proposed = models.BooleanField(_("Is proposed?"), default=False)

    name = models.CharField(
        _("Representative name"),
        max_length=254,
        blank=True,
        help_text=_("The name of the designated person in the organization."),
    )
    role = models.CharField(
        _("Representative role in organization"),
        max_length=254,
        blank=True,
        help_text=_("The role of the designated person in the organization."),
    )
    photo = models.ImageField(
        _("Candidate photo"),
        max_length=300,
        storage=select_public_storage,
        blank=True,
        default="",
        validators=[file_validator],
    )

    # files expected in different cases
    statement = models.FileField(
        _("Representative statement"),
        null=True,
        blank=True,
        max_length=300,
        help_text=_(
            "Declaration of the designated representative stating that he/she is not a member "
            "of the leadership of a political party, has not been elected to a public office "
            "and is not a dignitary of the Romanian state, has no criminal record."
        ),
        validators=[file_validator],
    )
    mandate = models.FileField(
        _("Mandate"),
        null=True,
        blank=True,
        max_length=300,
        help_text=_(
            "Mandate from the organization (signed in original + electronic) "
            "with the highlighting of the domain for which it is running"
        ),
        validators=[file_validator],
    )
    letter_of_intent = models.FileField(
        _("Letter of intent"),
        null=True,
        blank=True,
        max_length=300,
        help_text=_("Letter of intent (with the mention of the domain to be represented in the CES)"),
        validators=[file_validator],
    )
    cv = models.FileField(
        _("CV"),
        null=True,
        blank=True,
        max_length=300,
        help_text=_("Europass format CV"),
        validators=[file_validator],
    )
    declaration_of_interests = models.FileField(
        _("Declaration of interests"),
        null=True,
        blank=True,
        max_length=300,
        help_text=_("Official format Declaration of interests"),
        validators=[file_validator],
    )
    fiscal_record = models.FileField(
        _("Fiscal record"),
        null=True,
        blank=True,
        max_length=300,
        help_text=_("Fiscal record, valid at the time of submitting the candidacy"),
        validators=[file_validator],
    )
    criminal_record = models.FileField(
        _("Criminal record"),
        null=True,
        blank=True,
        max_length=300,
        help_text=_("(Optional) Criminal record, valid at the time of submitting the candidacy"),
        validators=[file_validator],
    )

    objects = models.Manager()
    objects_with_org = CandidatesWithOrgManager()
    proposed = CandidatesProposedManager()

    class Meta:
        verbose_name_plural = _("Candidates")
        verbose_name = _("Candidate")
        ordering = ["name"]

        permissions = (
            ("view_data_candidate", "View data candidate"),
            ("approve_candidate", "Approve candidate"),
            ("reset_approve_candidate", "Reset candidate approval"),
            ("support_candidate", "Support candidate"),
            ("vote_candidate", "Vote candidate"),
        )

    def __str__(self):
        return f"{self.org} ({self.name})"

    @staticmethod
    def file_fields():
        return (
            "photo",
            "statement",
            "mandate",
            "letter_of_intent",
            "cv",
            "declaration_of_interests",
            "fiscal_record",
            "criminal_record",
        )

    @classmethod
    def required_fields(cls):
        return [
            cls.photo,
            cls.domain,
            cls.name,
            cls.role,
            cls.statement,
            cls.mandate,
            cls.letter_of_intent,
            cls.cv,
            cls.declaration_of_interests,
            cls.fiscal_record,
        ]

    @property
    def is_complete(self):
        """
        Validate if the Org uploaded all the requested info to propose a Candidate
        """
        if not super().is_complete:
            return False

        if not FeatureFlag.flag_enabled("enable_voting_domain"):
            return True

        if self.domain != self.org.voting_domain:
            return False

        return True

    def get_absolute_url(self):
        return reverse("candidate-detail", args=[self.pk])

    def count_supporters(self):
        return self.supporters.count()

    def count_votes(self):
        return self.votes.count()

    def count_confirmations(self):
        confirmations = self.confirmations
        unique_confirmations = confirmations.values("user").distinct()
        return unique_confirmations.count()

    def update_users_permissions(self):
        for org_user in self.org.users.all():
            assign_perm("view_candidate", org_user, self)
            assign_perm("change_candidate", org_user, self)
            assign_perm("delete_candidate", org_user, self)
            assign_perm("view_data_candidate", org_user, self)

    def save(self, *args, **kwargs):
        create = False if self.id else True

        if self.id and CandidateVote.objects.filter(candidate=self).exists():
            raise ValidationError(_("Cannot update candidate after votes have been cast."))

        if FeatureFlag.flag_enabled("single_domain_round"):
            self.domain = Domain.objects.first()

        # This covers the flow when a candidate is withdrawn as the official proposal or the organization, while
        # in the same time keeping the old candidate record and backwards compatibility with the one-to-one relations
        # that are used in the rest of the codebase.
        # TODO: Refactor this flow to make it less hacky and have a single relationship back to organization.
        self.org: Organization
        if self.id and self.initial_org:
            self.org = None
            self.is_proposed = False

        super().save(*args, **kwargs)

        if create:
            self.update_users_permissions()


class CandidateAction(models.Model):
    user: UserModel = None
    candidate: Candidate = None

    class Meta:
        abstract = True

    def __str__(self):
        user_pk = self.user.pk
        user_full_name = self.user.get_full_name()

        user_identification = f"[u{user_pk}] {user_full_name}"

        if user_organization := self.user.organization:
            org_pk = user_organization.pk
            org_name = user_organization.name

            user_identification = f"[u{user_pk}–o{org_pk}] {user_full_name}–{org_name}"

        return f"{user_identification} - {self.candidate}"


class CandidateVote(TimeStampedModel, CandidateAction):
    user = models.ForeignKey(UserModel, on_delete=models.PROTECT)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)

    candidate = models.ForeignKey("Candidate", on_delete=models.CASCADE, related_name="votes")
    domain = models.ForeignKey("Domain", on_delete=models.PROTECT, related_name="votes")

    class Meta:
        verbose_name_plural = _("Candidate votes")
        verbose_name = _("Candidate vote")
        constraints = [
            models.UniqueConstraint(fields=["user", "candidate"], name="unique_candidate_vote"),
        ]

    def save(self, *args, **kwargs):
        self.domain = self.candidate.domain

        votes_for_domain = CandidateVote.objects.filter(organization=self.organization, domain=self.domain).count()
        if votes_for_domain >= self.domain.seats:
            raise Exception("Maximum number of votes reached")

        super().save(*args, **kwargs)


class CandidateSupporter(TimeStampedModel, CandidateAction):
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    candidate = models.ForeignKey("Candidate", on_delete=models.CASCADE, related_name="supporters")

    class Meta:
        verbose_name_plural = _("Canditate supporters")
        verbose_name = _("Candidate supporter")
        constraints = [
            models.UniqueConstraint(fields=["user", "candidate"], name="unique_candidate_supporter"),
        ]


class CandidateConfirmation(TimeStampedModel, CandidateAction):
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    candidate = models.ForeignKey("Candidate", on_delete=models.CASCADE, related_name="confirmations")

    class Meta:
        verbose_name_plural = _("Candidate confirmations")
        verbose_name = _("Candidate confirmation")
        constraints = [
            models.UniqueConstraint(fields=["user", "candidate"], name="unique_candidate_confirmation"),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        candidate: Candidate = self.candidate
        candidate_is_accepted: bool = candidate.status == Candidate.STATUS.accepted
        if candidate_is_accepted:
            candidate_has_all_confirmations: bool = (
                candidate.count_confirmations() >= User.objects.filter(groups__name=COMMITTEE_GROUP).count()
            )
            if candidate_has_all_confirmations:
                candidate.status = Candidate.STATUS.confirmed
                candidate.save()


base_exclude_fields = ["created", "modified"]
organization_exclude_fields = base_exclude_fields + [
    "ngohub_last_update_ended",
    "ngohub_last_update_started",
    "filename_cache",
]
auditlog.register(Organization, exclude_fields=base_exclude_fields)
auditlog.register(Candidate, exclude_fields=base_exclude_fields)
auditlog.register(CandidateVote, exclude_fields=base_exclude_fields)
auditlog.register(CandidateSupporter, exclude_fields=base_exclude_fields)
auditlog.register(CandidateConfirmation, exclude_fields=base_exclude_fields)
auditlog.register(FeatureFlag, exclude_fields=base_exclude_fields)
