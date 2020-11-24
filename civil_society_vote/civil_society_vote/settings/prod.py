from .base import *  # noqa

# Fail-safe: make sure that we never run DEBUG in production
DEBUG = TEMPLATE_DEBUG = False

SECRET_KEY = env.str("SECRET_KEY")  # noqa

# ALLOWED_HOSTS = ["votong.ro", "www.votong.ro"]

# STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# MIDDLEWARE.append("whitenoise.middleware.WhiteNoiseMiddleware")

STATIC_ROOT = os.path.join(BASE_DIR, "../", "static")
STATICFILES_DIRS = []
