from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.storage import get_storage_class
from django.db import models, transaction
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices
from model_utils.models import StatusModel, TimeStampedModel

ADMIN_GROUP_NAME = "Admin"

NGO_GROUP_NAME = "ONG"
CES_GROUP_NAME = "CES"
SGG_GROUP_NAME = "SGG"

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

VOTE = Choices(("yes", _("YES")), ("no", _("NO")), ("abstention", _("ABSTENTION")),)


STATE_CHOICES = Choices(("active", _("Active")), ("inactive", _("Inactive")),)


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

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="orgs")
    domain = models.ForeignKey("Domain", on_delete=models.PROTECT, related_name="orgs")

    name = models.CharField(_("NGO Name"), max_length=254)
    reg_com_number = models.CharField(_("Registration number"), max_length=20)
    state = models.CharField(_("Current state"), max_length=10, choices=STATE_CHOICES, default=STATE_CHOICES.active)
    purpose_initial = models.CharField(_("Initial purpose"), max_length=254)
    purpose_current = models.CharField(_("Current purpose"), max_length=254)
    founders = models.CharField(_("Founders/Associates"), max_length=254)
    representative = models.CharField(_("Legal representative"), max_length=254)
    board_council = models.CharField(_("Board council"), max_length=254)
    email = models.EmailField(_("Email"))
    phone = models.CharField(_("Phone"), max_length=30)
    county = models.CharField(_("County"), choices=COUNTY_CHOICES, max_length=50)
    city = models.ForeignKey("City", on_delete=models.PROTECT, null=True, verbose_name=_("City"))
    address = models.CharField(_("Address"), max_length=254)
    logo = models.ImageField(_("Logo"), max_length=300, storage=PublicMediaStorageClass())
    last_balance_sheet = models.FileField(
        _("First page of last balance sheet"), max_length=300, storage=PrivateMediaStorageClass(),
    )
    statute = models.FileField(_("NGO Statute"), max_length=300, storage=PrivateMediaStorageClass())
    letter = models.FileField(_("Letter of intent"), max_length=300, storage=PrivateMediaStorageClass())

    class Meta:
        verbose_name_plural = _("Organizations")
        verbose_name = _("Organization")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("ngo-detail", args=[self.pk])

    def save(self, *args, **kwargs):
        if self.city:
            self.county = self.city.county
        else:
            self.county = ""

        super().save(*args, **kwargs)

    def yes(self):
        return self.votes.filter(vote="YES").count()

    yes.short_description = _("Yes")

    def no(self):
        return self.votes.filter(vote="NO").count()

    no.short_description = _("No")

    def abstention(self):
        return self.votes.filter(vote="ABSTENTION").count()

    abstention.short_description = _("Abstention")

    def create_owner(self, request):
        user, created = User.objects.get_or_create(username=self.email)

        if not created:
            return user

        user.email = self.email
        user.set_password(get_random_string())
        user.is_active = True
        user.save()

        return user

    @transaction.atomic
    def accept(self, request):
        owner = self.create_owner(request)
        self.user = owner
        self.status = self.STATUS.accepted
        self.save()

    @transaction.atomic
    def reject(self, request):
        self.status = self.STATUS.rejected
        self.save()


class OrganizationVote(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    org = models.ForeignKey("Organization", on_delete=models.CASCADE, related_name="votes")
    domain = models.ForeignKey("Domain", on_delete=models.PROTECT, related_name="+")

    vote = models.CharField(_("Vote"), choices=VOTE, default=VOTE.abstention, max_length=10)
    motivation = models.TextField(
        _("Motivation"), max_length=500, null=True, blank=True, help_text=_("Motivate your decision"),
    )

    class Meta:
        verbose_name_plural = _("Organization votes")
        verbose_name = _("Organization vote")
        unique_together = [["user", "org"], ["user", "domain"]]
        constraints = [
            models.UniqueConstraint(fields=["user", "org"], name="unique_org_vote"),
            models.UniqueConstraint(fields=["user", "domain"], name="unique_org_domain_vote"),
        ]

    def __str__(self):
        return f"{self.vote} - {self.org}"

    def save(self, *args, **kwargs):
        self.domain = self.org.domain

        if self.vote == VOTE.NO and not self.motivation:
            raise ValidationError(_("You must specify a motivation if voting NO!"))

        super().save(*args, **kwargs)


class Candidate(TimeStampedModel):
    org = models.OneToOneField("Organization", on_delete=models.CASCADE, related_name="candidate")
    domain = models.ForeignKey("Domain", on_delete=models.PROTECT, related_name="candidates")

    name = models.CharField(_("Name"), max_length=254)
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
    cv = models.FileField(_("CV"), max_length=300, storage=PrivateMediaStorageClass())
    legal_record = models.FileField(_("Legal record"), max_length=300, storage=PrivateMediaStorageClass())

    class Meta:
        verbose_name_plural = _("Candidates")
        verbose_name = _("Candidate")

    def __str__(self):
        return f"{self.name} ({self.org})"

    def get_absolute_url(self):
        return reverse("candidate-detail", args=[self.pk])


class CandidateVote(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
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
