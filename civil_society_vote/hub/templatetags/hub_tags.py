from django import template

from hub.models import COMMITTEE_GROUP, STAFF_GROUP, SUPPORT_GROUP, CandidateVote

register = template.Library()


@register.filter
def already_voted_candidate_or_domain(user, candidate):
    if CandidateVote.objects.filter(user=user, candidate=candidate).exists():
        return True

    if CandidateVote.objects.filter(user=user, domain=candidate.domain).exists():
        return True

    return False


@register.filter
def can_view_orgs(user):
    if user.groups.filter(name__in=[COMMITTEE_GROUP, STAFF_GROUP, SUPPORT_GROUP]).exists():
        return True
    return False
