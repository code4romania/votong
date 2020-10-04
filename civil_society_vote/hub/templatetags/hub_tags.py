from django import template

from hub.models import COMMITTEE_GROUP, CandidateSupporter, CandidateVote

register = template.Library()


@register.filter
def already_voted_candidate_or_domain(user, candidate):
    if CandidateVote.objects.filter(user=user, candidate=candidate).exists():
        return True

    if CandidateVote.objects.filter(user=user, domain=candidate.domain).exists():
        return True

    return False


@register.filter
def in_committee_group(user):
    return user.groups.filter(name=COMMITTEE_GROUP).exists()


@register.simple_tag
def supporters(candidate_id):
    return CandidateSupporter.objects.filter(candidate=candidate_id).count()


@register.filter
def already_supported(user, candidate):
    if CandidateSupporter.objects.filter(user=user, candidate=candidate).exists():
        return True
    return False
