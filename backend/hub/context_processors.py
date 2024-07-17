from django.conf import settings

from hub.models import FLAG_CHOICES, FeatureFlag


def hub_settings(context):
    flags = {k: v for k, v in FeatureFlag.objects.all().values_list("flag", "is_enabled")}

    return {
        # Flags from settings.py:
        "ANALYTICS_ENABLED": settings.ANALYTICS_ENABLED,
        "CURRENT_EDITION_TYPE": settings.CURRENT_EDITION_TYPE,
        "CURRENT_EDITION_YEAR": settings.CURRENT_EDITION_YEAR,
        "DEBUG": settings.DEBUG,
        "ENABLE_ORG_REGISTRATION_FORM": settings.ENABLE_ORG_REGISTRATION_FORM,
        "NGOHUB_APP_BASE_URL": settings.NGOHUB_APP_BASE,
        # Flags from database:
        "CANDIDATE_REGISTRATION_ENABLED": flags.get(FLAG_CHOICES.enable_candidate_registration, False),
        "CANDIDATE_SUPPORTING_ENABLED": flags.get(FLAG_CHOICES.enable_candidate_supporting, False),
        "CANDIDATE_VOTING_ENABLED": flags.get(FLAG_CHOICES.enable_candidate_voting, False),
        "GLOBAL_SUPPORT_ENABLED": flags.get(FLAG_CHOICES.global_support_round, False),
        "ORG_APPROVAL_ENABLED": flags.get(FLAG_CHOICES.enable_org_approval, False),
        "ORG_REGISTRATION_ENABLED": flags.get(FLAG_CHOICES.enable_org_registration, False),
    }
