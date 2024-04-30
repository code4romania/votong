"""
Django settings for civil_society_vote project.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os

import environ
from django.urls import reverse_lazy  # noqa

root = environ.Path(__file__) - 3  # three folder back (/a/b/c/ - 3 = /)
env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False),
    ENABLE_DEBUG_TOOLBAR=(bool, False),
    USE_S3=(bool, False),
    ALLOWED_HOSTS=(list, [".votong.ro"]),
    RECAPTCHA_PUBLIC_KEY=(str, ""),
    RECAPTCHA_PRIVATE_KEY=(str, ""),
    SENTRY_DSN=(str, ""),
    ANALYTICS_ENABLED=(bool, False),
    GLOBAL_SUPPORT_ENABLED=(bool, False),
    # email settings
    EMAIL_SEND_METHOD=(str, "async"),
    EMAIL_BACKEND=(str, "django.core.mail.backends.console.EmailBackend"),
    EMAIL_HOST=(str, ""),
    EMAIL_PORT=(str, ""),
    EMAIL_HOST_USER=(str, ""),
    EMAIL_HOST_PASSWORD=(str, ""),
    EMAIL_USE_TLS=(str, ""),
    EMAIL_FAIL_SILENTLY=(bool, False),
    DEFAULT_FROM_EMAIL=(str, "no-reply@code4.ro"),
    NO_REPLY_EMAIL=(str, "no-reply@code4.ro"),
)
environ.Env.read_env(f"{root}/.env")  # reading .env file

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEBUG = env("DEBUG")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

SITE_ID = 1

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.humanize",
    # apps
    "hub",
    "accounts",
    # third-party
    "avatar",
    "admin_auto_filters",
    "spurl",
    "crispy_forms",
    # "django_crispy_bulma",
    "storages",
    "django_recaptcha",
    "file_resubmit",
    "rangefilter",
    "impersonate",
    "guardian",
    "ckeditor",
    "ckeditor_uploader",
]

MIDDLEWARE = [
    "civil_society_vote.middleware.ForceDefaultLanguageMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "impersonate.middleware.ImpersonateMiddleware",
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",  # this is the default
    "guardian.backends.ObjectPermissionBackend",
    "civil_society_vote.middleware.CaseInsensitiveUserModel",
]

ROOT_URLCONF = "civil_society_vote.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "hub.context_processors.hub_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "civil_society_vote.wsgi.application"

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DATABASE_NAME"),
        "USER": env("DATABASE_USER"),
        "PASSWORD": env("DATABASE_PASSWORD"),
        "HOST": env("DATABASE_HOST"),
        "PORT": env("DATABASE_PORT"),
    }
}


CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "file_resubmit": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": "/tmp/file_resubmit/",
    },
}

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "hub.password_validation.PasswordDifferentFromPrevious"},
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LOCALE_PATHS = (os.path.join(BASE_DIR, "../", "locale"),)

LANGUAGE_CODE = "ro"

LANGUAGES = (
    ("en", "English"),
    ("ro", "Română"),
)

TIME_ZONE = "Europe/Bucharest"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

USE_S3 = env("USE_S3")

if USE_S3:
    # aws settings
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_DEFAULT_ACL = "public-read"
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
    PUBLIC_MEDIA_LOCATION = "media"
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{PUBLIC_MEDIA_LOCATION}/"
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    # s3 public media settings
    PUBLIC_MEDIA_LOCATION = "media"
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{PUBLIC_MEDIA_LOCATION}/"
    DEFAULT_FILE_STORAGE = "hub.storage_backends.PublicMediaStorage"
    # s3 private media settings
    PRIVATE_MEDIA_LOCATION = "private"
    PRIVATE_FILE_STORAGE = "hub.storage_backends.PrivateMediaStorage"
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME")
    AWS_S3_SIGNATURE_VERSION = "s3v4"
else:
    PRIVATE_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
    MEDIA_URL = "/media/"
    MEDIA_ROOT = str(root.path("mediafiles"))

STATICFILES_DIRS = (str(root.path("static")),)
STATIC_ROOT = str(root.path("staticfiles"))
STATIC_URL = "/static/"


# Email settings
EMAIL_BACKEND = env.str("EMAIL_BACKEND")
EMAIL_SEND_METHOD = env.str("EMAIL_SEND_METHOD")
EMAIL_FAIL_SILENTLY = env.bool("EMAIL_FAIL_SILENTLY")

DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL")
NO_REPLY_EMAIL = env.str("NO_REPLY_EMAIL")

if EMAIL_BACKEND == "django_ses.SESBackend":
    AWS_SES_CONFIGURATION_SET_NAME = env.str("AWS_SES_CONFIGURATION_SET_NAME")

    AWS_SES_AUTO_THROTTLE = env.float("AWS_SES_AUTO_THROTTLE", default=0.5)
    AWS_SES_REGION_NAME = env.str("AWS_SES_REGION_NAME") if env("AWS_SES_REGION_NAME") else env("AWS_REGION_NAME")
    AWS_SES_REGION_ENDPOINT = env.str("AWS_SES_REGION_ENDPOINT", default=f"email.{AWS_SES_REGION_NAME}.amazonaws.com")

    AWS_SES_FROM_EMAIL = DEFAULT_FROM_EMAIL

    USE_SES_V2 = env.bool("AWS_SES_USE_V2", default=True)

    if aws_access_key := env("AWS_ACCESS_KEY_ID", default=None):
        AWS_ACCESS_KEY_ID = aws_access_key
        AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
else:
    EMAIL_HOST = env.str("EMAIL_HOST")
    EMAIL_PORT = env.str("EMAIL_PORT")
    EMAIL_HOST_USER = env.str("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD")
    EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS")


CRISPY_ALLOWED_TEMPLATE_PACKS = ("bulma",)
CRISPY_TEMPLATE_PACK = "bulma"

ADMINS = [
    ("Alexandra Stefanescu", "alexandra.stefanescu@code4.ro"),
]

# The email where the votes are sent for archiving purposes
VOTE_AUDIT_EMAIL = env("VOTE_AUDIT_EMAIL", default="logs@votong.ro")

LOGIN_URL = reverse_lazy("login")
LOGIN_REDIRECT_URL = reverse_lazy("home")
LOGOUT_REDIRECT_URL = reverse_lazy("home")

# Recaptcha settings
RECAPTCHA_PUBLIC_KEY = env("RECAPTCHA_PUBLIC_KEY", default="")
RECAPTCHA_PRIVATE_KEY = env("RECAPTCHA_PRIVATE_KEY", default="")

if not RECAPTCHA_PUBLIC_KEY:
    SILENCED_SYSTEM_CHECKS = ["captcha.recaptcha_test_key_error"]

# Toggles the loading of Google/Facebook tracking scripts in base.html
ANALYTICS_ENABLED = env("ANALYTICS_ENABLED")

IMPERSONATE = {
    "REQUIRE_SUPERUSER": True,
}

AVATAR_THUMB_FORMAT = "PNG"
AVATAR_ADD_TEMPLATE = "avatar/change.html"
AVATAR_PROVIDERS = (
    "avatar.providers.PrimaryAvatarProvider",
    "avatar.providers.DefaultAvatarProvider",
)
AVATAR_DEFAULT_URL = "/images/photo-placeholder.gif"

CKEDITOR_BASEPATH = f"{STATIC_URL}ckeditor/ckeditor/"
CKEDITOR_CONFIGS = {
    "default": {"toolbar": "full", "height": 600, "width": 950},
}
CKEDITOR_UPLOAD_PATH = "uploads/"

if env("SENTRY_DSN"):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=env("SENTRY_DSN"),
        integrations=[DjangoIntegration()],
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,
        environment="staging" if DEBUG else "prod",
    )

GLOBAL_SUPPORT_ENABLED = env("GLOBAL_SUPPORT_ENABLED")
