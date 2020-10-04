from accounts.models import User
from ckeditor.fields import RichTextField
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.storage import get_storage_class
from django.db import models
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
from guardian.shortcuts import assign_perm
from model_utils import Choices
from model_utils.models import StatusModel, TimeStampedModel

# NOTE: If you change the group names here, make sure you also update the names in the live database before deployment
STAFF_GROUP = "Code4Romania Staff"
COMMITTEE_GROUP = "Comisie Electorala"
SUPPORT_GROUP = "Support Staff"
NGO_GROUP = "ONG"


PrivateMediaStorageClass = get_storage_class(settings.PRIVATE_FILE_STORAGE)
PublicMediaStorageClass = get_storage_class(settings.DEFAULT_FILE_STORAGE)


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

STATE_CHOICES = Choices(("active", _("Active")), ("inactive", _("Inactive")),)

FLAG_CHOICES = Choices(
    ("enable_org_registration", _("Enable organization registration")),
    ("enable_org_approval", _("Enable organization approvals")),
    ("enable_org_voting", _("Enable organization voting")),
    ("enable_candidate_registration", _("Enable candidate registration")),
    ("enable_candidate_supporting", _("Enable candidate supporting")),
    ("enable_candidate_voting", _("Enable candidate voting")),
)

EMAIL_TEMPLATE_CHOICES = Choices(
    ("pending_orgs_digest", _("Pending organizations digest email")),
    ("org_approved", _("Your organization was approved")),
    ("org_rejected", _("Your organization was rejected")),
)


class FeatureFlag(TimeStampedModel):
    flag = models.CharField(_("Flag"), choices=FLAG_CHOICES, max_length=254, unique=True)
    is_enabled = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Feature flag")
        verbose_name_plural = _("Feature flags")

    def __str__(self):
        return f"{FLAG_CHOICES[self.flag]}"


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
    STATUS = Choices(("pending", _("Pending")), ("accepted", _("Accepted")), ("rejected", _("Rejected")),)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="orgs"
    )

    name = models.CharField(_("NGO Name"), max_length=254)
    county = models.CharField(_("County"), choices=COUNTY_CHOICES, max_length=50)
    city = models.ForeignKey("City", on_delete=models.PROTECT, null=True, verbose_name=_("City"))
    address = models.CharField(_("Address"), max_length=254)
    email = models.EmailField(_("Organisation Email"))
    phone = models.CharField(_("Organisation Phone"), max_length=30, null=True, blank=True)
    description = models.TextField(_("Short Description"), null=True, blank=True)
    legal_representative_name = models.CharField(_("Legal Representative Name"), max_length=254)
    legal_representative_email = models.EmailField(_("Legal Representative Email"))
    legal_representative_phone = models.CharField(_("Legal Representative Phone"), max_length=30, null=True, blank=True)
    organisation_head_name = models.CharField(_("Organisation Head Name"), max_length=254)
    board_council = models.CharField(_("Board council"), max_length=512)
    logo = models.ImageField(_("Logo"), max_length=300, storage=PublicMediaStorageClass())
    last_balance_sheet = models.FileField(
        _("First page of last balance sheet"), max_length=300, storage=PrivateMediaStorageClass(),
    )
    statute = models.FileField(_("NGO Statute"), max_length=300, storage=PrivateMediaStorageClass())
    # founders = models.CharField(_("Founders/Associates"), max_length=254)
    # reg_com_number = models.CharField(_("Registration number"), max_length=20)
    # state = models.CharField(_("Current state"), max_length=10, choices=STATE_CHOICES, default=STATE_CHOICES.active)
    # purpose_initial = models.CharField(_("Initial purpose"), max_length=254)
    # purpose_current = models.CharField(_("Current purpose"), max_length=254)
    # representative = models.CharField(_("Legal representative"), max_length=254)
    # letter = models.FileField(_("Letter of intent"), max_length=300, storage=PrivateMediaStorageClass())

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
        user, created = User.objects.get_or_create(username=self.email)

        if not created:
            return user

        user.email = self.email
        user.set_password(get_random_string())
        user.is_active = True
        user.save()

        # Add organization user to the NGO group
        user.groups.add(Group.objects.get(name=NGO_GROUP))

        return user


class Candidate(StatusModel, TimeStampedModel):
    STATUS = Choices(("pending", _("Pending")), ("accepted", _("Accepted")), ("rejected", _("Rejected")),)

    org = models.OneToOneField("Organization", on_delete=models.CASCADE, related_name="candidate")
    domain = models.ForeignKey("Domain", on_delete=models.PROTECT, related_name="candidates")

    name = models.CharField(_("Name"), max_length=254)
    description = models.TextField(_("Description"))
    role = models.CharField(_("Role"), max_length=254)
    founder = models.BooleanField(_("Founder/Associate"), default=False)
    representative = models.BooleanField(_("Legal representative"), default=False)
    board_member = models.BooleanField(_("Board member"), default=False)
    experience = models.TextField(_("Professional experience"))
    studies = models.TextField(_("Studies"))
    email = models.EmailField(_("Email"))
    phone = models.CharField(_("Phone"), max_length=30)
    photo = models.ImageField(_("Photo"), max_length=300, storage=PublicMediaStorageClass())

    mandate = models.FileField(_("Mandate from the organization"), max_length=300, storage=PrivateMediaStorageClass(),)
    letter = models.FileField(_("Letter of intent"), max_length=300, storage=PrivateMediaStorageClass())
    statement = models.FileField(_("Statement of conformity"), max_length=300, storage=PrivateMediaStorageClass(),)
    cv = models.FileField(_("Curriculum Vitae"), max_length=300, storage=PrivateMediaStorageClass())
    legal_record = models.FileField(_("Legal record"), max_length=300, storage=PrivateMediaStorageClass())

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
        return f"{self.name} ({self.org})"

    def get_absolute_url(self):
        return reverse("candidate-detail", args=[self.pk])

    def vote_count(self):
        return self.votes.count()

    vote_count.short_description = _("Vote count")

    def save(self, *args, **kwargs):
        create = False if self.id else True

        if self.id and CandidateVote.objects.filter(candidate=self).exists():
            raise ValidationError(_("Cannot update candidate after votes have been cast."))

        super().save(*args, **kwargs)

        if create:
            assign_perm("view_candidate", self.org.user, self)
            assign_perm("change_candidate", self.org.user, self)
            assign_perm("delete_candidate", self.org.user, self)
            assign_perm("view_data_candidate", self.org.user, self)

            assign_perm("approve_candidate", Group.objects.get(name=COMMITTEE_GROUP), self)
            assign_perm("view_data_candidate", Group.objects.get(name=COMMITTEE_GROUP), self)
            assign_perm("view_data_candidate", Group.objects.get(name=STAFF_GROUP), self)
            assign_perm("view_data_candidate", Group.objects.get(name=SUPPORT_GROUP), self)

            assign_perm("support_candidate", Group.objects.get(name=NGO_GROUP), self)
            assign_perm("vote_candidate", Group.objects.get(name=NGO_GROUP), self)


class CandidateVote(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    candidate = models.ForeignKey("Candidate", on_delete=models.CASCADE, related_name="votes")
    domain = models.ForeignKey("Domain", on_delete=models.PROTECT, related_name="votes")

    class Meta:
        verbose_name_plural = _("Canditate votes")
        verbose_name = _("Candidate vote")
        constraints = [
            models.UniqueConstraint(fields=["user", "candidate"], name="unique_candidate_vote"),
            models.UniqueConstraint(fields=["user", "domain"], name="unique_candidate_domain_vote"),
        ]

    def __str__(self):
        return f"{self.user} - {self. candidate}"

    def save(self, *args, **kwargs):
        self.domain = self.candidate.domain
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
        return f"{self.user} - {self. candidate}"
