from typing import Any, Dict

from django.conf import settings
from django.http import HttpRequest
from django.urls import reverse

from hub.models import FLAG_CHOICES, FeatureFlag, SETTINGS_CHOICES


def hub_settings(_: HttpRequest) -> Dict[str, Any]:
    flags = {k: v for k, v in FeatureFlag.objects.all().values_list("flag", "is_enabled")}

    register_url = settings.NGOHUB_APP_BASE
    if settings.ENABLE_ORG_REGISTRATION_FORM:
        register_url = reverse("ngos-register-request")

    candidate_registration_enabled = flags.get(FLAG_CHOICES.enable_candidate_registration, False)
    candidate_editing_enabled = flags.get(FLAG_CHOICES.enable_candidate_editing, False)
    candidate_supporting_enabled = flags.get(FLAG_CHOICES.enable_candidate_supporting, False)
    candidate_voting_enabled = flags.get(FLAG_CHOICES.enable_candidate_voting, False)
    candidate_confirmation_enabled = flags.get(FLAG_CHOICES.enable_candidate_confirmation, False)
    results_enabled = flags.get(FLAG_CHOICES.enable_results_display, False)
    org_approval_enabled = flags.get(FLAG_CHOICES.enable_org_approval, False)
    org_registration_enabled = flags.get(FLAG_CHOICES.enable_org_registration, False)

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
        "CANDIDATE_REGISTRATION_ENABLED": candidate_registration_enabled,
        "CANDIDATE_EDIT_ENABLED": candidate_editing_enabled,
        "CANDIDATE_SUPPORTING_ENABLED": candidate_supporting_enabled,
        "CANDIDATE_VOTING_ENABLED": candidate_voting_enabled,
        "CANDIDATE_CONFIRMATION_ENABLED": candidate_confirmation_enabled,
        "RESULTS_ENABLED": results_enabled,
        "ORG_APPROVAL_ENABLED": org_approval_enabled,
        "ORG_REGISTRATION_ENABLED": org_registration_enabled,
        # Settings flags
        "GLOBAL_SUPPORT_ENABLED": flags.get(SETTINGS_CHOICES.global_support_round, False),
        "VOTING_DOMAIN_ENABLED": flags.get(SETTINGS_CHOICES.enable_voting_domain, False),
        "SINGLE_DOMAIN_ROUND": flags.get(SETTINGS_CHOICES.single_domain_round, False),
        # Composite flags
        "ELECTION_IN_PROGRESS": (
            candidate_registration_enabled
            or candidate_supporting_enabled
            or candidate_voting_enabled
            or candidate_confirmation_enabled
            or org_registration_enabled
        ),
    }
