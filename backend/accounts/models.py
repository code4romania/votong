from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext as _


class User(AbstractUser):
    USERNAME_FIELD = "email"
    email = models.EmailField(_("email address"), unique=True)
    REQUIRED_FIELDS = []
