import logging

from django.contrib.auth import get_user_model
from tinymce.models import HTMLField
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.storage import storages
from django.db import models
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from guardian.shortcuts import assign_perm
from model_utils import Choices
from model_utils.models import StatusModel, TimeStampedModel

from accounts.models import User, STAFF_GROUP, COMMITTEE_GROUP, SUPPORT_GROUP, NGO_GROUP


REPORTS_HELP_TEXT = (
    "Rapoartele anuale trebuie să includă sursele de finanțare din care să rezulte că organizația dispune de resurse "
    "financiare şi umane pentru îndeplinirea mandatului de membru în Comisia Electorală a VotONG."
)

logger = logging.getLogger(__name__)


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
    ("enable_org_approval", _("Enable organization approvals")),
    ("enable_candidate_registration", _("Enable candidate registration")),
    ("enable_candidate_supporting", _("Enable candidate supporting")),
    ("enable_candidate_voting", _("Enable candidate voting")),
    ("enable_candidate_confirmation", _("Enable candidate confirmation")),
    ("enable_results_display", _("Enable the display of results")),
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
    def flag_enabled(flag: str) -> bool:
        """
        Check if the requested feature flag is enabled
        """
        if not flag:
            return False

        return FeatureFlag.objects.filter(flag=flag, is_enabled=True).exists()


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


class Organization(StatusModel, TimeStampedModel):
    # DRAFT: empty organization created by us, it might be invalid (e.g., created for another user of an org
    # PENDING: the organization doesn't have all the necessary documents
    # ACCEPTED: the organization has all required documentation and can vote
    # REJECTED: the organization was rejected by the electoral commission
    STATUS = Choices(
        ("draft", _("Draft")),
        ("pending", _("Pending approval")),
        ("ngohub_accepted", _("NGO Hub accepted")),
        ("accepted", _("Accepted")),
        ("rejected", _("Rejected")),
    )
    status = models.CharField(_("Status"), choices=STATUS, default=STATUS.draft, max_length=30, db_index=True)

    user = models.ForeignKey(UserModel, on_delete=models.SET_NULL, null=True, blank=True, related_name="orgs")

    ngohub_org_id = models.PositiveBigIntegerField(_("NGO Hub linked organization ID"), default=0, db_index=True)

    name = models.CharField(_("NGO Name"), max_length=254, blank=True, default="")
    county = models.CharField(_("County"), choices=COUNTY_CHOICES, max_length=50, blank=True, default="")
    city = models.ForeignKey("City", verbose_name=_("City"), on_delete=models.PROTECT, null=True, blank=True)
    address = models.CharField(_("Address"), max_length=254, blank=True, default="")
    registration_number = models.CharField(_("Registration number"), max_length=20, blank=True, default="")
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
    logo = models.FileField(_("Logo"), max_length=300, storage=select_public_storage, blank=True, default="")

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

    report_2023 = models.FileField(
        _("Yearly report 2023"),
        blank=True,
        default="",
        max_length=300,
        help_text=REPORTS_HELP_TEXT,
    )
    report_2022 = models.FileField(
        _("Yearly report 2022"),
        blank=True,
        default="",
        max_length=300,
        help_text=REPORTS_HELP_TEXT,
    )
    report_2021 = models.FileField(
        _("Yearly report 2021"),
        blank=True,
        default="",
        max_length=300,
        help_text=REPORTS_HELP_TEXT,
    )

    statement_discrimination = models.FileField(
        _("Non-discrimination statement"),
        blank=True,
        default="",
        max_length=300,
        help_text="Declarație pe proprie răspundere prin care declară că nu realizează activități sau susține cauze de natură politică sau care discriminează pe considerente legate de etnie, rasă, sex, orientare sexuală, religie, capacități fizice sau psihice sau de apartenența la una sau mai multe categorii sociale sau economice.",
    )
    statement_political = models.FileField(
        _("Non-political statement"),
        blank=True,
        default="",
        max_length=300,
        help_text="Declarație pe propria răspundere prin care declar că ONG-ul nu are între membrii conducerii organizației (Președinte sau Consiliul Director) membri ai conducerii unui partid politic sau persoane care au fost alese într-o funcție publică.",
    )

    fiscal_certificate_anaf = models.FileField(
        _("Fiscal certificate ANAF"),
        blank=True,
        default="",
        max_length=300,
        help_text="Certificat fiscal emis de ANAF",
    )
    fiscal_certificate_local = models.FileField(
        _("Fiscal certificate local"),
        blank=True,
        default="",
        max_length=300,
        help_text="Certificat fiscal emis de Direcția de Impozite și Taxe Locale",
    )

    accept_terms_and_conditions = models.BooleanField(_("Accepted Terms and Conditions"), default=False)

    rejection_message = models.TextField(_("Rejection message"), blank=True)

    filename_cache = models.JSONField(_("Filename cache"), editable=False, default=dict, blank=False, null=False)

    ngohub_last_update_started = models.DateTimeField(_("Last NGO Hub update"), null=True, blank=True, editable=False)
    ngohub_last_update_ended = models.DateTimeField(_("Last NGO Hub update"), null=True, blank=True, editable=False)

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
    def required_fields():
        fields = [
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
            "board_council",
            "last_balance_sheet",
            "statute",
        ]

        if FeatureFlag.flag_enabled(FLAG_CHOICES.enable_voting_domain):
            fields.append("voting_domain")

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

    @property
    def is_complete(self):
        """
        Validate that the Org uploaded all the requested info to propose a Candidate
        """
        required_reports = []
        for year in range(
            settings.CURRENT_EDITION_YEAR - settings.PREV_REPORTS_REQUIRED_FOR_PROPOSAL, settings.CURRENT_EDITION_YEAR
        ):
            required_reports.append(getattr(self, f"report_{year}", None))

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
            + list(map(lambda x: getattr(self, x), self.required_fields()))
        )

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
        # Remove votes for candidates that are not in the voting domain
        for candidate in self.candidates.all():
            if candidate.is_proposed:
                candidate.delete()

        # Remove support that the organization has given
        CandidateSupporter.objects.filter(user__org=self).delete()

        # Remove votes that the organization has given
        CandidateVote.objects.filter(user__org=self).delete()

    def save(self, *args, **kwargs):
        create = False if self.id else True

        if self.pk and self.status == self.STATUS.accepted and FeatureFlag.flag_enabled("enable_voting_domain"):
            old_voting_domain = Organization.objects.filter(pk=self.pk).values_list("voting_domain", flat=True).first()
            if old_voting_domain and (not self.voting_domain or self.voting_domain.pk != old_voting_domain):
                self._remove_votes_supports_candidates()

        if self.city:
            self.county = self.city.county
        else:
            self.county = ""

        if self.status == self.STATUS.ngohub_accepted and self.voting_domain:
            self.status = self.STATUS.accepted

        if self.status == self.STATUS.accepted and not self.users.exists():
            self.create_owner()

        super().save(*args, **kwargs)

        if self.users:
            for user in self.users.all():
                assign_perm("view_data_organization", user, self)
                assign_perm("view_organization", user, self)
                assign_perm("change_organization", user, self)

        if create:
            assign_perm("view_data_organization", Group.objects.get(name=STAFF_GROUP), self)
            assign_perm("view_data_organization", Group.objects.get(name=SUPPORT_GROUP), self)

            assign_perm("view_data_organization", Group.objects.get(name=COMMITTEE_GROUP), self)
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


class Candidate(StatusModel, TimeStampedModel):
    # PENDING: has been created/proposed and is waiting for support from organizations
    # ACCEPTED: has been accepted by the admins of the platform
    # CONFIRMED: has received confirmation from the electoral commission
    # REJECTED: has been rejected
    STATUS = Choices(
        ("pending", _("Pending")),
        ("accepted", _("Accepted")),
        ("confirmed", _("Confirmed")),
        ("rejected", _("Rejected")),
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

    name = models.CharField(
        _("Representative name"),
        max_length=254,
        blank=True,
        help_text=_(
            "The name of the designated person who will represent the organization "
            "in the Electoral Commission in case of a favorable response."
            "The designated person must be an employee of the organization and part of its management structures "
            "(member of the Board of Directors, Executive Director, etc.)."
        ),
    )
    role = models.CharField(
        _("Representative role in organization"),
        max_length=254,
        blank=True,
        help_text=_("The role of the designated person in the organization."),
    )
    photo = models.ImageField(
        _("Candidate photo"), max_length=300, storage=select_public_storage, blank=True, default=""
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
            "and is not a dignitary of the Romanian state."
        ),
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
    )
    letter_of_intent = models.FileField(
        _("Letter of intent"),
        null=True,
        blank=True,
        max_length=300,
        help_text=_("Letter of intent (with the mention of the domain to be represented in the CES)"),
    )
    cv = models.FileField(
        _("CV"),
        null=True,
        blank=True,
        max_length=300,
        help_text=_("Europass format CV"),
    )
    declaration_of_interests = models.FileField(
        _("Declaration of interests"),
        null=True,
        blank=True,
        max_length=300,
        help_text=_("Official format Declaration of interests"),
    )
    fiscal_record = models.FileField(
        _("Fiscal record"),
        null=True,
        blank=True,
        max_length=300,
        help_text=_("Fiscal record, valid at the time of submitting the candidacy"),
    )
    criminal_record = models.FileField(
        _("Criminal record"),
        null=True,
        blank=True,
        max_length=300,
        help_text=_("(Optional) Criminal record, valid at the time of submitting the candidacy"),
    )

    is_proposed = models.BooleanField(_("Is proposed?"), default=False)

    objects = models.Manager()
    objects_with_org = CandidatesWithOrgManager()

    class Meta:
        verbose_name_plural = _("Candidates")
        verbose_name = _("Candidate")
        ordering = ["name"]

        permissions = (
            ("view_data_candidate", "View data candidate"),
            ("approve_candidate", "Approve candidate"),
            ("support_candidate", "Support candidate"),
            ("vote_candidate", "Vote candidate"),
        )

    def __str__(self):
        return f"{self.org} ({self.name})"

    @property
    def is_complete(self):
        """
        Validate if the Org uploaded all the requested info to propose a Candidate
        """
        if not all(
            [
                self.photo,
                self.domain,
                self.name,
                self.role,
                self.statement,
                self.mandate,
                self.letter_of_intent,
                self.cv,
                self.declaration_of_interests,
                self.fiscal_record,
            ]
        ):
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
            assign_perm("view_candidate", self.org.user, self)
            assign_perm("change_candidate", self.org.user, self)
            assign_perm("delete_candidate", self.org.user, self)
            assign_perm("view_data_candidate", self.org.user, self)


class CandidateVote(TimeStampedModel):
    user = models.ForeignKey(UserModel, on_delete=models.PROTECT)
    candidate = models.ForeignKey("Candidate", on_delete=models.CASCADE, related_name="votes")
    domain = models.ForeignKey("Domain", on_delete=models.PROTECT, related_name="votes")

    class Meta:
        verbose_name_plural = _("Candidate votes")
        verbose_name = _("Candidate vote")
        constraints = [
            models.UniqueConstraint(fields=["user", "candidate"], name="unique_candidate_vote"),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self. candidate}"

    def save(self, *args, **kwargs):
        self.domain = self.candidate.domain

        votes_for_domain = CandidateVote.objects.filter(user=self.user, domain=self.domain).count()
        if votes_for_domain >= self.domain.seats:
            raise Exception("Maximum number of votes reached")

        super().save(*args, **kwargs)


class CandidateSupporter(TimeStampedModel):
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    candidate = models.ForeignKey("Candidate", on_delete=models.CASCADE, related_name="supporters")

    class Meta:
        verbose_name_plural = _("Canditate supporters")
        verbose_name = _("Candidate supporter")
        constraints = [
            models.UniqueConstraint(fields=["user", "candidate"], name="unique_candidate_supporter"),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self. candidate}"


class CandidateConfirmation(TimeStampedModel):
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    candidate = models.ForeignKey("Candidate", on_delete=models.CASCADE, related_name="confirmations")

    class Meta:
        verbose_name_plural = _("Candidate confirmations")
        verbose_name = _("Candidate confirmation")
        constraints = [
            models.UniqueConstraint(fields=["user", "candidate"], name="unique_candidate_confirmation"),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self. candidate}"

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
