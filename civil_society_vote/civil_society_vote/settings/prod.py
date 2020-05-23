from .base import *  # noqa

DEBUG = False

SECRET_KEY = env.str("SECRET_KEY")  # noqa

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
