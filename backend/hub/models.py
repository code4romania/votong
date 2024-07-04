import logging

from ckeditor_uploader.fields import RichTextUploadingField
from ckeditor.fields import RichTextField
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

from accounts.models import User


# NOTE: If you change the group names here, make sure you also update the names in the live database before deployment
STAFF_GROUP = "Code4Romania Staff"
COMMITTEE_GROUP = "Comisie Electorala"
SUPPORT_GROUP = "Support Staff"
NGO_GROUP = "ONG"

REPORTS_HELP_TEXT = (
    "Rapoartele anuale trebuie să includă sursele de finanțare din care să rezulte că organizația dispune de resurse "
    "financiare şi umane pentru îndeplinirea mandatului de membru în Comisia Electorală a VotONG."
)

logger = logging.getLogger(__name__)


def select_public_storage():
    return storages["public"]


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

FLAG_CHOICES = Choices(
    ("enable_org_registration", _("Enable organization registration")),
    ("enable_org_approval", _("Enable organization approvals")),
    ("enable_org_voting", _("Enable organization voting")),
    ("enable_candidate_registration", _("Enable candidate registration")),
    ("enable_candidate_supporting", _("Enable candidate supporting")),
    ("enable_candidate_voting", _("Enable candidate voting")),
    ("single_domain_round", _("Voting round with just one domain (some restrictions will apply)")),
    ("global_support_round", _("Enable global support (the support of at least 10 organizations is required)")),
)

EMAIL_TEMPLATE_CHOICES = Choices(
    ("pending_orgs_digest", _("Pending organizations digest email")),
    ("org_approved", _("Your organization was approved")),
    ("org_rejected", _("Your organization was rejected")),
    ("vote_audit", _("Vote audit log")),
    ("confirmation", _("Confirmation email")),
)


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


class BlogPost(TimeStampedModel):
    title = models.CharField(_("Title"), max_length=254)
    slug = models.SlugField(unique=True)
    author = models.CharField(_("Author"), max_length=100)
    content_preview = models.TextField(_("Content preview"))
    content = RichTextUploadingField(
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


class EmailTemplate(TimeStampedModel):
    template = models.CharField(_("Template"), choices=EMAIL_TEMPLATE_CHOICES, max_length=254, unique=True)
    text_content = models.TextField(_("Text content"))
    html_content = RichTextField(_("HTML content"), blank=True)

    class Meta:
        verbose_name = _("Email template")
        verbose_name_plural = _("Email templates")

    def __str__(self):
        return f"{EMAIL_TEMPLATE_CHOICES[self.template]}"


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
    STATUS = Choices(
        ("draft", _("Draft")),
        ("pending", _("Pending approval")),
        ("accepted", _("Accepted")),
        ("rejected", _("Rejected")),
        # ("eligible", _("Eligible to vote")),
        # ("ineligible", _("Ineligible to vote")),
        # ("disabled", _("Disabled")),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="orgs"
    )

    ngohub_org_id = models.PositiveBigIntegerField(_("NGO Hub linked organization ID"), default=0, db_index=True)

    name = models.CharField(_("NGO Name"), max_length=254)
    county = models.CharField(_("County"), choices=COUNTY_CHOICES, max_length=50)
    city = models.ForeignKey("City", on_delete=models.PROTECT, null=True, verbose_name=_("City"))
    address = models.CharField(_("Address"), max_length=254)
    registration_number = models.CharField(_("Registration number"), max_length=20)

    email = models.EmailField(_("Organization Email"))
    phone = models.CharField(_("Organization Phone"), max_length=30, null=True, blank=True)
    description = models.TextField(_("Short Description"), null=True, blank=True)

    legal_representative_name = models.CharField(_("Legal Representative Name"), max_length=254)
    legal_representative_email = models.EmailField(_("Legal Representative Email"))
    legal_representative_phone = models.CharField(_("Legal Representative Phone"), max_length=30, null=True, blank=True)

    organization_head_name = models.CharField(_("Organization Head Name"), default="", max_length=254)
    board_council = models.CharField(_("Board council"), max_length=512)
    logo = models.ImageField(_("Logo"), max_length=300, storage=select_public_storage)
    logo_url = models.URLField(_("Logo URL"), max_length=300, blank=True)

    last_balance_sheet = models.FileField(
        _("First page of last balance sheet for %(CURRENT_EDITION_YEAR)s")
        % {"CURRENT_EDITION_YEAR": str(settings.CURRENT_EDITION_YEAR)},
        null=True,
        max_length=300,
    )
    statute = models.FileField(
        _("NGO Statute"),
        null=True,
        max_length=300,
        help_text="Copie a ultimului statut autentificat al organizației și a hotărârii judecătorești corespunzătoare, definitivă şi irevocabilă și copii ale tuturor documentelor ulterioare/suplimentare ale statutului, inclusiv hotărârile judecătorești definitive și irevocabile; Vă rugăm să arhivați documentele și să încărcați o singură arhivă în platformă.",
    )

    report_2023 = models.FileField(
        _("Yearly report 2023"),
        null=True,
        blank=True,
        max_length=300,
        help_text=REPORTS_HELP_TEXT,
    )
    report_2022 = models.FileField(
        _("Yearly report 2022"),
        null=True,
        blank=True,
        max_length=300,
        help_text=REPORTS_HELP_TEXT,
    )
    report_2021 = models.FileField(
        _("Yearly report 2021"),
        null=True,
        blank=True,
        max_length=300,
        help_text=REPORTS_HELP_TEXT,
    )

    report_2020 = models.FileField(
        _("Yearly report 2020"),
        null=True,
        blank=True,
        max_length=300,
        help_text=REPORTS_HELP_TEXT,
    )
    report_2019 = models.FileField(
        _("Yearly report 2019"),
        null=True,
        blank=True,
        max_length=300,
        help_text=REPORTS_HELP_TEXT,
    )
    report_2018 = models.FileField(
        _("Yearly report 2018"),
        null=True,
        blank=True,
        max_length=300,
        help_text=REPORTS_HELP_TEXT,
    )
    report_2017 = models.FileField(
        _("Yearly report 2017"),
        null=True,
        blank=True,
        max_length=300,
        help_text=REPORTS_HELP_TEXT,
    )

    statement_discrimination = models.FileField(
        _("Non-discrimination statement"),
        null=True,
        blank=True,
        max_length=300,
        help_text="Declarație pe proprie răspundere prin care declară că nu realizează activități sau susține cauze de natură politică sau care discriminează pe considerente legate de etnie, rasă, sex, orientare sexuală, religie, capacități fizice sau psihice sau de apartenența la una sau mai multe categorii sociale sau economice.",
    )
    statement_political = models.FileField(
        _("Non-political statement"),
        null=True,
        blank=True,
        max_length=300,
        help_text="Declarație pe propria răspundere prin care declar că ONG-ul nu are între membrii conducerii organizației (Președinte sau Consiliul Director) membri ai conducerii unui partid politic sau persoane care au fost alese într-o funcție publică.",
    )

    fiscal_certificate_anaf = models.FileField(
        _("Fiscal certificate ANAF"),
        null=True,
        blank=True,
        max_length=300,
        help_text="Certificat fiscal emis de ANAF",
    )
    fiscal_certificate_local = models.FileField(
        _("Fiscal certificate local"),
        null=True,
        blank=True,
        max_length=300,
        help_text="Certificat fiscal emis de Direcția de Impozite și Taxe Locale",
    )

    accept_terms_and_conditions = models.BooleanField(_("Accepted Terms and Conditions"), default=False)

    rejection_message = models.TextField(_("Rejection message"), blank=True)

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
            return self.logo_url

    @property
    def edit_only_on_nghohub(self):
        """
        Organizations managed elsewhere (ie: on NGO Hub) should not be editable here
        """
        if self.ngohub_org_id and not settings.NGOHUB_ORG_OVERWRITE:
            return True
        return False

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
        )

    def get_absolute_url(self):
        return reverse("ngo-detail", args=[self.pk])

    def save(self, *args, **kwargs):
        create = False if self.id else True

        if self.city:
            self.county = self.city.county
        else:
            self.county = ""

        if self.status == self.STATUS.accepted and not self.user:
            owner = self.create_owner()
            self.user = owner

        super().save(*args, **kwargs)

        if self.user:
            assign_perm("view_data_organization", self.user, self)
            assign_perm("view_organization", self.user, self)
            assign_perm("change_organization", self.user, self)

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
        user.save()

        # Add organization user to the NGO group
        user.groups.add(Group.objects.get(name=NGO_GROUP))

        return user


class CandidatesWithOrgManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(org=None)


class Candidate(StatusModel, TimeStampedModel):
    STATUS = Choices(
        ("pending", _("Pending")),
        ("accepted", _("Accepted")),
        ("rejected", _("Rejected")),
    )

    org = models.OneToOneField(
        "Organization", on_delete=models.CASCADE, related_name="candidate", null=True, blank=True
    )
    initial_org = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        related_name="candidates",
        null=True,
        blank=True,
        help_text=_(
            "If this is set, the `org` field will be unset and the candidate is removed as the official proposal of the organization."
        ),
    )
    domain = models.ForeignKey(
        "Domain", verbose_name=_("Domain"), on_delete=models.PROTECT, related_name="candidates", null=True, blank=True
    )

    name = models.CharField(
        _("Representative name"),
        max_length=254,
        blank=True,
        help_text="Numele persoanei care va reprezenta organizatia in Comisia Electorală în cazul unui răspuns favorabil. Persoana desemnată trebuie să fie angajat în cadrul organizației și parte din structurile de conducere ale acesteia (membru în Consiliul Director, Director Executiv etc)",
    )
    role = models.CharField(
        _("Representative role in organization"),
        max_length=254,
        blank=True,
        help_text="Funcția în organizației a persoanei desemnate.",
    )
    statement = models.FileField(
        _("Representative statement"),
        null=True,
        blank=True,
        max_length=300,
        help_text="Declarație pe propria răspundere a reprezentantului desemnat prin care declară că nu este membru al conducerii unui partid politic, nu a fost ales într-o funcție publică și nu este demnitar al statului român.",
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
        Validate if the Org uploaded all the requested info to proppose a Candidate
        """
        return all(
            [
                self.domain,
                self.name,
                self.role,
                self.statement,
            ]
        )

    def get_absolute_url(self):
        return reverse("candidate-detail", args=[self.pk])

    def save(self, *args, **kwargs):
        create = False if self.id else True

        if self.id and CandidateVote.objects.filter(candidate=self).exists():
            raise ValidationError(_("Cannot update candidate after votes have been cast."))

        if FeatureFlag.objects.filter(flag="single_domain_round", is_enabled=True).exists():
            self.domain = Domain.objects.first()

        # This covers the flow when a candidate is withdrawn as the official proposal or the organization, while
        # in the same time keeping the old candidate record and backwards compatibility with the one-to-one relations
        # that are used in the rest of the codebase.
        # TODO: Refactor this flow to make it less hacky and have a single relationship back to organization.
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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    candidate = models.ForeignKey("Candidate", on_delete=models.CASCADE, related_name="votes")
    domain = models.ForeignKey("Domain", on_delete=models.PROTECT, related_name="votes")

    class Meta:
        verbose_name_plural = _("Canditate votes")
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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    candidate = models.ForeignKey("Candidate", on_delete=models.CASCADE, related_name="confirmations")

    class Meta:
        verbose_name_plural = _("Canditate confirmations")
        verbose_name = _("Candidate confirmation")
        constraints = [
            models.UniqueConstraint(fields=["user", "candidate"], name="unique_candidate_confirmation"),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self. candidate}"
