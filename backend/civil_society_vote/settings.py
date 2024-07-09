"""
Django settings for civil_society_vote project.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os
from copy import deepcopy
from pathlib import Path

import environ
import sentry_sdk
from django.urls import reverse_lazy  # noqa


# Constants for memory sizes
KIBIBYTE = 1024
MEBIBYTE = KIBIBYTE * 1024
GIBIBYTE = MEBIBYTE * 1024
TEBIBYTE = GIBIBYTE * 1024


# Environment parameters
root = Path(__file__).resolve().parent.parent.parent

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = os.path.abspath(os.path.join(root, "backend"))


SILENCED_SYSTEM_CHECKS = ["ckeditor.W001"]


env = environ.Env(
    # aws settings
    USE_S3=(bool, False),
    AWS_REGION_NAME=(str, ""),
    AWS_S3_STORAGE_DEFAULT_BUCKET_NAME=(str, ""),
    AWS_S3_STORAGE_PUBLIC_BUCKET_NAME=(str, ""),
    AWS_S3_DEFAULT_ACL=(str, "private"),
    AWS_S3_PUBLIC_ACL=(str, "public-read"),
    AWS_S3_DEFAULT_PREFIX=(str, ""),
    AWS_S3_PUBLIC_PREFIX=(str, ""),
    AWS_S3_REGION_NAME=(str, ""),
    AWS_S3_DEFAULT_CUSTOM_DOMAIN=(str, ""),
    AWS_S3_PUBLIC_CUSTOM_DOMAIN=(str, ""),
    AWS_S3_CUSTOM_DOMAIN=(str, ""),
    AWS_SES_REGION_NAME=(str, ""),
    AWS_SES_INCLUDE_REPORTS=(bool, False),
    AWS_SES_CONFIGURATION_SET_NAME=(str, None),
    AWS_COGNITO_REGION=(str, ""),
    AWS_COGNITO_DOMAIN=(str, ""),
    AWS_COGNITO_USER_POOL_ID=(str, ""),
    AWS_COGNITO_CLIENT_ID=(str, ""),
    AWS_COGNITO_CLIENT_SECRET=(str, ""),
    # azure settings
    USE_AZURE=(bool, False),
    AZURE_ACCOUNT_NAME=(str, ""),
    AZURE_ACCOUNT_KEY=(str, ""),
    AZURE_CONTAINER=(str, "data"),
    # django settings
    DEBUG=(bool, False),
    ENABLE_DEBUG_TOOLBAR=(bool, False),
    ENVIRONMENT=(str, "production"),
    SECRET_KEY=(str, "replace-with-a-secret-key"),
    LOGLEVEL=(str, "INFO"),
    ALLOWED_HOSTS=(list, ["*"]),
    IS_CONTAINERIZED=(bool, False),
    LANGUAGE_CODE=(str, "ro"),
    TIME_ZONE=(str, "Europe/Bucharest"),
    AUDITLOG_EXPIRY_DAYS=(int, 45),
    DATA_UPLOAD_MAX_MEMORY_SIZE=(int, 3 * MEBIBYTE),
    MAX_DOCUMENT_SIZE=(int, 2 * MEBIBYTE),
    # db settings
    # DATABASE_ENGINE=(str, "sqlite3"),
    DATABASE_NAME=(str, "default"),
    DATABASE_USER=(str, "root"),
    DATABASE_PASSWORD=(str, ""),
    DATABASE_HOST=(str, "localhost"),
    DATABASE_PORT=(str, "5432"),
    # Sentry
    SENTRY_DSN=(str, ""),
    SENTRY_TRACES_SAMPLE_RATE=(float, 0),
    SENTRY_PROFILES_SAMPLE_RATE=(float, 0),
    # django-q2 settings
    BACKGROUND_WORKERS_COUNT=(int, 1),
    # recaptcha settings
    RECAPTCHA_PUBLIC_KEY=(str, ""),
    RECAPTCHA_PRIVATE_KEY=(str, ""),
    # TODO Settings Cleanup:
    ANALYTICS_ENABLED=(bool, False),
    NGOHUB_ORG_OVERWRITE=(bool, False),
    ORGANIZATION_UPDATE_THRESHOLD=(int, 10),
    ENABLE_ORG_REGISTRATION_FORM=(bool, False),
    CURRENT_EDITION_YEAR=(int, 2024),
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
    # ngo hub api settings
    NGOHUB_API_HOST=(str, "api-staging.ngohub.ro"),
    NGOHUB_API_ACCOUNT=(str, ""),
    NGOHUB_API_KEY=(str, ""),
)

# reading .env file
dot_env_path = os.path.abspath(os.path.join(root, ".env"))
environ.Env.read_env(dot_env_path)

# SECURITY WARNING: keep the secret key used in production secret
SECRET_KEY = env("SECRET_KEY")

DEBUG = env("DEBUG")
ENVIRONMENT = env.str("ENVIRONMENT")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# some settings will be different if it's not running in a container (e.g., locally, on a Mac)
IS_CONTAINERIZED = env.bool("IS_CONTAINERIZED")

VERSION = env.str("VERSION", "edge")
REVISION = env.str("REVISION", "develop")

if IS_CONTAINERIZED and VERSION == "edge" and REVISION == "develop":
    version_file = "/var/www/votong/.version"
    if os.path.exists(version_file):
        with open(version_file) as f:
            VERSION, REVISION = f.read().strip().split("+")
            REVISION = REVISION[:7]


SITE_ID = 1


USE_S3 = env.bool("USE_S3")
USE_AZURE = env.bool("USE_AZURE") and env("AZURE_ACCOUNT_NAME") and env("AZURE_ACCOUNT_KEY")
AWS_SES_INCLUDE_REPORTS = env.bool("AWS_SES_INCLUDE_REPORTS")
AWS_REGION_NAME = env("AWS_REGION_NAME")

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
    "utils",
    # authentication
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.amazon_cognito",
    # other third-party
    "avatar",
    "admin_auto_filters",
    "spurl",
    "crispy_forms",
    "django_crispy_bulma",
    "storages",
    "django_q",
    "django_recaptcha",
    "file_resubmit",
    "rangefilter",
    "impersonate",
    "guardian",
    "ckeditor",
    "ckeditor_uploader",
]

if not (USE_S3 or USE_AZURE):
    INSTALLED_APPS.append("whitenoise.runserver_nostatic")

if AWS_SES_INCLUDE_REPORTS:
    INSTALLED_APPS.append("django_ses")


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
    "allauth.account.middleware.AccountMiddleware",
]

if DEBUG and env("ENABLE_DEBUG_TOOLBAR"):
    INSTALLED_APPS += ["debug_toolbar", "django_extensions"]
    MIDDLEWARE.insert(1, "debug_toolbar.middleware.DebugToolbarMiddleware")

    def show_toolbar(request):
        return True

    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": show_toolbar,
    }

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",  # this is the default
    "guardian.backends.ObjectPermissionBackend",
    "civil_society_vote.middleware.CaseInsensitiveUserModel",
    "allauth.account.auth_backends.AuthenticationBackend",
]

ROOT_URLCONF = "civil_society_vote.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.abspath(os.path.join(BASE_DIR, "templates"))],
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

ENABLE_CACHE = env.bool("ENABLE_CACHE", default=not DEBUG)
if ENABLE_CACHE:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": "factory_cache_default",
            "TIMEOUT": 600,  # default cache timeout in seconds
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        }
    }
CACHES["file_resubmit"] = {
    "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
    "LOCATION": "/tmp/file_resubmit/",
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

# superuser/admin seed data
DJANGO_ADMIN_PASSWORD = env.str("DJANGO_ADMIN_PASSWORD", None)
DJANGO_ADMIN_EMAIL = env.str("DJANGO_ADMIN_EMAIL", None)


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LOCALE_PATHS = (os.path.join(BASE_DIR, "locale"),)

LANGUAGE_CODE = env("LANGUAGE_CODE")

LANGUAGES = (
    ("en", "English"),
    ("ro", "Română"),
)

TIME_ZONE = env("TIME_ZONE")
USE_I18N = True
USE_TZ = True

#
# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

public_static_location = "static"
public_media_location = "media"
private_media_location = "media"

STATIC_URL = f"{public_static_location}/"
MEDIA_URL = f"{public_media_location}/"

STATIC_ROOT = os.path.abspath(os.path.join(BASE_DIR, "static"))
MEDIA_ROOT = os.path.abspath(os.path.join(BASE_DIR, "media"))

media_storage = "django.core.files.storage.FileSystemStorage"
static_storage = "whitenoise.storage.CompressedStaticFilesStorage"

default_storage_options = {}
public_storage_options = {}

if env.bool("USE_S3"):
    media_storage = "storages.backends.s3boto3.S3Boto3Storage"
    static_storage = "storages.backends.s3boto3.S3StaticStorage"

    # https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html
    default_storage_options = {
        "bucket_name": (env.str("AWS_S3_STORAGE_DEFAULT_BUCKET_NAME")),
        "default_acl": (env.str("AWS_S3_DEFAULT_ACL")),
        "region_name": env.str("AWS_S3_REGION_NAME") or AWS_REGION_NAME,
        "object_parameters": {"CacheControl": "max-age=86400"},
        "file_overwrite": False,
    }

    if aws_session_profile := env.str("AWS_S3_SESSION_PROFILE", default=None):
        default_storage_options["session_profile"] = aws_session_profile
    elif aws_access_key := env.str("AWS_ACCESS_KEY_ID", default=None):
        default_storage_options["access_key"] = aws_access_key
        default_storage_options["secret_key"] = env.str("AWS_SECRET_ACCESS_KEY")

    if default_prefix := env.str("AWS_S3_DEFAULT_PREFIX", default=None):
        default_storage_options["location"] = default_prefix

    if custom_domain := (
        env.str("AWS_S3_CUSTOM_DOMAIN", default=None) or env.str("AWS_S3_DEFAULT_CUSTOM_DOMAIN", default=None)
    ):
        default_storage_options["custom_domain"] = custom_domain

    public_storage_options = deepcopy(default_storage_options)
    if public_acl := env.str("AWS_S3_PUBLIC_ACL"):
        public_storage_options["default_acl"] = public_acl
    if public_bucket_name := env.str("AWS_S3_STORAGE_PUBLIC_BUCKET_NAME"):
        public_storage_options["bucket_name"] = public_bucket_name
    if public_prefix := env.str("AWS_S3_PUBLIC_PREFIX", default=None):
        public_storage_options["location"] = public_prefix
    if custom_domain := (
        env.str("AWS_S3_CUSTOM_DOMAIN", default=None) or env.str("AWS_S3_PUBLIC_CUSTOM_DOMAIN", default=None)
    ):
        public_storage_options["custom_domain"] = custom_domain
elif USE_AZURE:
    media_storage = "storages.backends.azure_storage.AzureStorage"
    static_storage = "storages.backends.azure_storage.AzureStorage"

    # https://django-storages.readthedocs.io/en/latest/backends/azure.html
    if azure_connection_string := env("AZURE_CONNECTION_STRING", default=None):
        default_storage_options["connection_string"] = azure_connection_string
    else:
        default_storage_options["account_name"] = env("AZURE_ACCOUNT_NAME")
        default_storage_options["account_key"] = env("AZURE_ACCOUNT_KEY")

    default_storage_options["azure_container"] = env("AZURE_CONTAINER")

    azure_custom_domain = f"{env('AZURE_ACCOUNT_NAME')}.blob.core.windows.net"
    default_storage_options["custom_domain"] = azure_custom_domain

    # azure public media settings
    MEDIA_URL = f"https://{azure_custom_domain}/{public_media_location}/"

STORAGES = {
    "default": {
        "BACKEND": media_storage,
        "LOCATION": private_media_location,
        "OPTIONS": default_storage_options,
    },
    "public": {
        "BACKEND": media_storage,
        "LOCATION": public_media_location,
        "OPTIONS": public_storage_options,
    },
    "staticfiles": {
        "BACKEND": static_storage,
        "LOCATION": public_static_location,
        "OPTIONS": public_storage_options,
    },
}

if IS_CONTAINERIZED:
    STATIC_ROOT = os.path.abspath(os.path.join(os.sep, "var", "www", "votong", "backend", "static"))
    MEDIA_ROOT = os.path.abspath(os.path.join(os.sep, "var", "www", "votong", "backend", "media"))

# Maximum request size excludind the uploaded files
DATA_UPLOAD_MAX_MEMORY_SIZE = env.int("DATA_UPLOAD_MAX_MEMORY_SIZE")

# Maximum single file size for uploaded files
MAX_DOCUMENT_SIZE = env.int("MAX_DOCUMENT_SIZE")

STATICFILES_DIRS = (os.path.abspath(os.path.join(BASE_DIR, "static_extras")),)


# Email settings
EMAIL_BACKEND = env.str("EMAIL_BACKEND")
EMAIL_SEND_METHOD = env.str("EMAIL_SEND_METHOD")
EMAIL_FAIL_SILENTLY = env.bool("EMAIL_FAIL_SILENTLY")

DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL")
CONTACT_EMAIL = env.str("CONTACT_EMAIL", default=DEFAULT_FROM_EMAIL)
NO_REPLY_EMAIL = env.str("NO_REPLY_EMAIL")

if EMAIL_BACKEND == "django_ses.SESBackend":
    AWS_SES_CONFIGURATION_SET_NAME = env.str("AWS_SES_CONFIGURATION_SET_NAME")

    AWS_SES_AUTO_THROTTLE = env.float("AWS_SES_AUTO_THROTTLE", default=0.5)
    AWS_SES_REGION_NAME = env.str("AWS_SES_REGION_NAME") if env("AWS_SES_REGION_NAME") else AWS_REGION_NAME
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


# Django Q2
# https://django-q2.readthedocs.io/en/stable/brokers.html

Q_CLUSTER = {
    "name": "votong",
    "workers": env.int("BACKGROUND_WORKERS_COUNT"),
    "recycle": 100,
    "timeout": 900,  # A task must finish in less than 15 minutes
    "retry": 1200,  # Retry an unfinished task after 20 minutes
    "ack_failures": True,
    "max_attempts": 2,
    "compress": True,
    "save_limit": 200,
    "queue_limit": 4,
    "cpu_affinity": 1,
    "label": "Django Q2",
    "orm": "default",
    "poll": 2,
    "guard_cycle": 3,
    "catch_up": False,
}


CRISPY_ALLOWED_TEMPLATE_PACKS = ("bulma",)
CRISPY_TEMPLATE_PACK = "bulma"


# The email where the votes are sent for archiving purposes
VOTE_AUDIT_EMAIL = env("VOTE_AUDIT_EMAIL", default="logs@votong.ro")

LOGIN_URL = reverse_lazy("login")
LOGIN_REDIRECT_URL = reverse_lazy("home")
LOGOUT_REDIRECT_URL = reverse_lazy("home")

# Recaptcha settings
RECAPTCHA_PUBLIC_KEY = env("RECAPTCHA_PUBLIC_KEY", default="")
RECAPTCHA_PRIVATE_KEY = env("RECAPTCHA_PRIVATE_KEY", default="")
RECAPTCHA_REQUIRED_SCORE = 0.70

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

# Django logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env.str("LOGLEVEL"),
    },
}

# Sentry
if env.str("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=env.str("SENTRY_DSN"),
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE"),
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        profiles_sample_rate=env.float("SENTRY_PROFILES_SAMPLE_RATE"),
        environment=ENVIRONMENT,
        release=f"votong@{VERSION}+{REVISION}",
    )


# Django Allauth settings
SOCIALACCOUNT_PROVIDERS = {
    "amazon_cognito": {
        "DOMAIN": "https://" + env.str("AWS_COGNITO_DOMAIN"),
        "EMAIL_AUTHENTICATION": True,  # TODO
        "VERIFIED_EMAIL": True,  # TODO
        "APPS": [
            {
                "client_id": env.str("AWS_COGNITO_CLIENT_ID"),
                "secret": env.str("AWS_COGNITO_CLIENT_SECRET"),
            },
        ],
    }
}

SOCIALACCOUNT_ADAPTER = "hub.social_adapters.UserOrgAdapter"

# Django Allauth allow only social logins
SOCIALACCOUNT_ONLY = True
ACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_STORE_TOKENS = False

NGOHUB_API_BASE = f"https://{env('NGOHUB_API_HOST')}/"
NGOHUB_API_ACCOUNT = env("NGOHUB_API_ACCOUNT")
NGOHUB_API_KEY = env("NGOHUB_API_KEY")

AWS_COGNITO_REGION = env("AWS_COGNITO_REGION") or AWS_REGION_NAME
AWS_COGNITO_USER_POOL_ID = env("AWS_COGNITO_USER_POOL_ID")
AWS_COGNITO_CLIENT_ID = env("AWS_COGNITO_CLIENT_ID")
AWS_COGNITO_CLIENT_SECRET = env("AWS_COGNITO_CLIENT_SECRET")

# Allow Organization data to overwrite from VotONG forms (should be False)
NGOHUB_ORG_OVERWRITE = env("NGOHUB_ORG_OVERWRITE")
ORGANIZATION_UPDATE_THRESHOLD = env.int("ORGANIZATION_UPDATE_THRESHOLD", 10)

# Enable the organization registration form in order to sidestep NGO Hub (should be False)
ENABLE_ORG_REGISTRATION_FORM = env("ENABLE_ORG_REGISTRATION_FORM")

CURRENT_EDITION_YEAR = env("CURRENT_EDITION_YEAR")

# How many previous year reports to require for a candidate proposal
PREV_REPORTS_REQUIRED_FOR_PROPOSAL = 3
