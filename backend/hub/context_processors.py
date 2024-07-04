from django.conf import settings

from hub.models import FLAG_CHOICES, FeatureFlag


def hub_settings(context):
    flags = {k: v for k, v in FeatureFlag.objects.all().values_list("flag", "is_enabled")}

    return {
        "DEBUG": settings.DEBUG,
        "CURRENT_EDITION_YEAR": settings.CURRENT_EDITION_YEAR,
        "ANALYTICS_ENABLED": settings.ANALYTICS_ENABLED,
        "GLOBAL_SUPPORT_ENABLED": flags.get(FLAG_CHOICES.global_support_round, False),
        "ORG_REGISTRATION_ENABLED": flags.get(FLAG_CHOICES.enable_org_registration, False),
        "ORG_APPROVAL_ENABLED": flags.get(FLAG_CHOICES.enable_org_approval, False),
        "CANDIDATE_REGISTRATION_ENABLED": flags.get(FLAG_CHOICES.enable_candidate_registration, False),
        "CANDIDATE_SUPPORTING_ENABLED": flags.get(FLAG_CHOICES.enable_candidate_supporting, False),
        "CANDIDATE_VOTING_ENABLED": flags.get(FLAG_CHOICES.enable_candidate_voting, False),
    }
