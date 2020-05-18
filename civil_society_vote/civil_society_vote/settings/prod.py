from .base import *  # noqa

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration


sentry_sdk.init(
    dsn=env.str("SENTRY_DSN"),  # noqa
    integrations=[DjangoIntegration()],
    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True,
)

SECRET_KEY = env.str("SECRET_KEY")  # noqa

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
