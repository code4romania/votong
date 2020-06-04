from django import template

from hub.models import ORG_VOTERS_GROUP, CandidateVote

register = template.Library()


@register.filter
def can_vote_candidate(user, candidate):
    if CandidateVote.objects.filter(user=user, candidate=candidate).exists():
        return False

    if CandidateVote.objects.filter(user=user, domain=candidate.domain).exists():
        return False

    return True


@register.filter
def in_org_voters_group(user):
    if user.groups.filter(name=ORG_VOTERS_GROUP).exists():
        return True
    return False
