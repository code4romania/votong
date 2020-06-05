from django import template

from hub.models import ORG_VOTERS_GROUP, CandidateVote, OrganizationVote

register = template.Library()


@register.filter
def already_voted_candidate_or_domain(user, candidate):
    if CandidateVote.objects.filter(user=user, candidate=candidate).exists():
        return True

    if CandidateVote.objects.filter(user=user, domain=candidate.domain).exists():
        return True

    return False


@register.filter
def in_org_voters_group(user):
    if user.groups.filter(name=ORG_VOTERS_GROUP).exists():
        return True
    return False


@register.filter
def already_voted_org(user, org):
    if OrganizationVote.objects.filter(user=user, org=org).exists():
        return True

    return False


@register.simple_tag
def user_org_vote_obj(user, org):
    qs = OrganizationVote.objects.filter(user=user, org=org)

    if not qs.exists():
        return None

    return qs.first()
