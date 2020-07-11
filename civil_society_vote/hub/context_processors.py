from django.conf import settings

from hub.models import FeatureFlag


def hub_settings(context):
    org_voting_enabled = FeatureFlag.objects.filter(flag="enable_org_voting", status=FeatureFlag.STATUS.on).exists()
    candidate_voting_enabled = FeatureFlag.objects.filter(
        flag="enable_candidate_voting", status=FeatureFlag.STATUS.on
    ).exists()

    return {
        "DEBUG": settings.DEBUG,
        "ANALYTICS_ENABLED": settings.ANALYTICS_ENABLED,
        "ORG_VOTING_ENABLED": org_voting_enabled,
        "CANDIDATE_VOTING_ENABLED": candidate_voting_enabled,
    }
