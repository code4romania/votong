import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "civil_society_vote.settings")

application = get_wsgi_application()
