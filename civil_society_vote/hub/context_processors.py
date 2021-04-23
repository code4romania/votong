from django.conf import settings

from hub.models import FeatureFlag, Election


def hub_settings(context):
    flags = {k: v for k, v in FeatureFlag.objects.all().values_list("flag", "is_enabled")}

    return {
        "DEBUG": settings.DEBUG,
        "ANALYTICS_ENABLED": settings.ANALYTICS_ENABLED,
        "ORG_REGISTRATION_ENABLED": flags["enable_org_registration"],
        "ORG_APPROVAL_ENABLED": flags["enable_org_approval"],
        "CANDIDATE_REGISTRATION_ENABLED": flags["enable_candidate_registration"],
        "CANDIDATE_SUPPORTING_ENABLED": flags["enable_candidate_supporting"],
        "CANDIDATE_VOTING_ENABLED": flags["enable_candidate_voting"],
    }


def active_election(context):
    return { 
        "ACTIVE_ELECTION": Election.get_active_election() ,
    }
