from .base import *

DEBUG = True

SECRET_KEY = "really_secret"

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = ["whitenoise.runserver_nostatic"] + INSTALLED_APPS

AUTH_PASSWORD_VALIDATORS = []

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# No Google/Facebook trackers in the dev env
ANALYTICS_ENABLED = False

if env("ENABLE_DEBUG_TOOLBAR"):
    INSTALLED_APPS += ["debug_toolbar", "django_extensions"]
    MIDDLEWARE.insert(1, "debug_toolbar.middleware.DebugToolbarMiddleware")

    def show_toolbar(request):
        return True

    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": show_toolbar,
    }
