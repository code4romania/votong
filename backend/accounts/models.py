from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext as _


# NOTE: If you change the group names here, make sure you also update the names in the live database before deployment
STAFF_GROUP = "Code4Romania Staff"
COMMITTEE_GROUP = "Comisie Electorala"
SUPPORT_GROUP = "Support Staff"
NGO_GROUP = "ONG"


class User(AbstractUser):
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
    is_ngohub_user = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        constraints = [
            models.UniqueConstraint(Lower("email"), name="email_unique"),
        ]

    def get_cognito_id(self):
        social = self.socialaccount_set.filter(provider="amazon_cognito").last()
        if social:
            return social.uid
        return None

    def in_committee_or_staff_groups(self):
        return self.groups.filter(name__in=[COMMITTEE_GROUP, STAFF_GROUP, SUPPORT_GROUP]).exists()

    def in_commission_groups(self):
        return (
            self.groups.filter(name=COMMITTEE_GROUP).exists()
            and not self.groups.filter(name__in=[STAFF_GROUP, SUPPORT_GROUP]).exists()
        )

    def in_staff_groups(self):
        return self.groups.filter(name__in=[STAFF_GROUP, SUPPORT_GROUP]).exists()
