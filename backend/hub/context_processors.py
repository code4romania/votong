from typing import Any, Dict

from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.urls import reverse

from hub.models import FLAG_CHOICES, FeatureFlag


def hub_settings(_: WSGIRequest) -> Dict[str, Any]:
    flags = {k: v for k, v in FeatureFlag.objects.all().values_list("flag", "is_enabled")}

    register_url = settings.NGOHUB_APP_BASE
    if settings.ENABLE_ORG_REGISTRATION_FORM:
        register_url = reverse("ngos-register-request")

    return {
        # Flags from settings.py:
        "ANALYTICS_ENABLED": settings.ANALYTICS_ENABLED,
        "CURRENT_EDITION_TYPE": settings.CURRENT_EDITION_TYPE,
        "CURRENT_EDITION_YEAR": settings.CURRENT_EDITION_YEAR,
        "DEBUG": settings.DEBUG,
        "REGISTER_URL": register_url,
        "NGOHUB_HOME": settings.NGOHUB_HOME_HOST,
        "NGOHUB_HOME_FULL": settings.NGOHUB_HOME_BASE,
        "CONTACT_EMAIL": settings.CONTACT_EMAIL,
        "COMISSION_EMAIL": settings.COMISSION_EMAIL,
        # Flags from database:
        "CANDIDATE_REGISTRATION_ENABLED": flags.get(FLAG_CHOICES.enable_candidate_registration, False),
        "CANDIDATE_SUPPORTING_ENABLED": flags.get(FLAG_CHOICES.enable_candidate_supporting, False),
        "CANDIDATE_VOTING_ENABLED": flags.get(FLAG_CHOICES.enable_candidate_voting, False),
        "CANDIDATE_CONFIRMATION_ENABLED": flags.get(FLAG_CHOICES.enable_candidate_confirmation, False),
        "RESULTS_ENABLED": flags.get(FLAG_CHOICES.enable_results_display, False),
        "ORG_APPROVAL_ENABLED": flags.get(FLAG_CHOICES.enable_org_approval, False),
        "ORG_REGISTRATION_ENABLED": flags.get(FLAG_CHOICES.enable_org_registration, False),
        # Settings flags
        "GLOBAL_SUPPORT_ENABLED": flags.get(FLAG_CHOICES.global_support_round, False),
        "VOTING_DOMAIN_ENABLED": flags.get(FLAG_CHOICES.enable_voting_domain, False),
    }
