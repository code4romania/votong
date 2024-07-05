from django.conf import settings

from hub.models import FeatureFlag


def hub_settings(context):
    flags = {k: v for k, v in FeatureFlag.objects.all().values_list("flag", "is_enabled")}

    return {
        "DEBUG": settings.DEBUG,
        "CURRENT_EDITION_YEAR": settings.CURRENT_EDITION_YEAR,
        "ANALYTICS_ENABLED": settings.ANALYTICS_ENABLED,
        "ENABLE_ORG_REGISTRATION_FORM": settings.ENABLE_ORG_REGISTRATION_FORM,
        "GLOBAL_SUPPORT_ENABLED": flags.get("global_support_enabled", False),
        "ORG_REGISTRATION_ENABLED": flags.get("enable_org_registration", False),
        "ORG_APPROVAL_ENABLED": flags.get("enable_org_approval", False),
        "CANDIDATE_REGISTRATION_ENABLED": flags.get("enable_candidate_registration", False),
        "CANDIDATE_SUPPORTING_ENABLED": flags.get("enable_candidate_supporting", False),
        "CANDIDATE_VOTING_ENABLED": flags.get("enable_candidate_voting", False),
    }
