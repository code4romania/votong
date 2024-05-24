from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext as _


class User(AbstractUser):
    # We ignore the "username" field because we will use the email for the authentication
    username = models.CharField(
        verbose_name=_("username"),
        max_length=150,
        unique=True,
        help_text=_("We do not use this field"),
        validators=[],
        null=True,
        editable=False,
    )
    email = models.EmailField(verbose_name=_("email address"), blank=False, null=False, unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        constraints = [
            models.UniqueConstraint(Lower("email"), name="email_unique"),
        ]
