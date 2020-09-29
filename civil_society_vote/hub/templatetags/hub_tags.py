from django import template

from hub.models import COMMITTEE_GROUP, STAFF_GROUP, SUPPORT_GROUP, CandidateVote, OrganizationVote

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
    if user.groups.filter(name=COMMITTEE_GROUP).exists():
        return True
    return False


@register.filter
def in_staff_group(user):
    if user.groups.filter(name=STAFF_GROUP).exists():
        return True
    return False


@register.filter
def in_support_group(user):
    if user.groups.filter(name=SUPPORT_GROUP).exists():
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
