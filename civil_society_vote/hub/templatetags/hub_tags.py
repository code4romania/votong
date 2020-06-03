from django import template

from hub.models import CandidateVote

register = template.Library()


@register.filter
def can_vote_candidate(user, candidate):
    if CandidateVote.objects.filter(user=user, candidate=candidate).exists():
        return False

    if CandidateVote.objects.filter(user=user, domain=candidate.domain).exists():
        return False

    return True
