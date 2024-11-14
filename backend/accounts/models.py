from auditlog.registry import auditlog
from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.db.models.functions import Lower
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from model_utils.models import TimeStampedModel

from civil_society_vote.common.cache import cache_decorator

# NOTE: If you change the group names here, make sure you also update the names in the live database before deployment
STAFF_GROUP = "Code4Romania Staff"
COMMITTEE_GROUP = "Comisie Electorala"
SUPPORT_GROUP = "Support Staff"
NGO_GROUP = "ONG"
NGO_USERS_GROUP = "ONG Users"


class User(AbstractUser, TimeStampedModel):
    # We ignore the "username" field because we will use the email for the authentication
    username = models.CharField(
        verbose_name=_("username"),
        max_length=150,
        unique=True,
        help_text=_("We do not use this field"),
        validators=[],
        null=True,
    )
    email = models.EmailField(verbose_name=_("email address"), blank=False, null=False, unique=True)
    is_ngohub_user = models.BooleanField(verbose_name=_("is ngo hub user"), default=False)

    organization = models.ForeignKey(
        "hub.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        constraints = [
            models.UniqueConstraint(Lower("email"), name="email_unique"),
        ]

    def org_user_pks(self):
        if not self.organization:
            return []

        return self.organization.users.values_list("pk", flat=True)

    def get_cognito_id(self):
        social = self.socialaccount_set.filter(provider="amazon_cognito").last()
        if social:
            return social.uid
        return None

    def make_staff(self):
        if self.groups.filter(name=NGO_GROUP).exists():
            self.groups.remove(Group.objects.get(name=NGO_GROUP))
        if self.groups.filter(name=NGO_USERS_GROUP).exists():
            self.groups.remove(Group.objects.get(name=NGO_USERS_GROUP))

        self.groups.add(Group.objects.get(name=SUPPORT_GROUP))

        self.is_staff = True
        self.save()

    @method_decorator(
        cache_decorator(timeout=settings.TIMEOUT_CACHE_NORMAL, cache_key_prefix="committee_or_staff_groups")
    )
    def in_committee_or_staff_groups(self):
        return self.groups.filter(name__in=[COMMITTEE_GROUP, STAFF_GROUP, SUPPORT_GROUP]).exists()

    @method_decorator(cache_decorator(timeout=settings.TIMEOUT_CACHE_NORMAL, cache_key_prefix="commission_groups"))
    def in_commission_groups(self):
        return (
            self.groups.filter(name=COMMITTEE_GROUP).exists()
            and not self.groups.filter(name__in=[STAFF_GROUP, SUPPORT_GROUP]).exists()
        )

    @method_decorator(cache_decorator(timeout=settings.TIMEOUT_CACHE_NORMAL, cache_key_prefix="staff_groups"))
    def in_staff_groups(self):
        return self.groups.filter(name__in=[STAFF_GROUP, SUPPORT_GROUP]).exists()


class GroupProxy(Group):
    class Meta:
        proxy = True

        verbose_name = _("Group")
        verbose_name_plural = _("Groups")


auditlog.register(User, exclude_fields=["password"])
auditlog.register(GroupProxy)
