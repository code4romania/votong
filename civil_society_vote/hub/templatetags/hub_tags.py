from django import template
from django.db.models import Count

from hub.models import (
    COMMITTEE_GROUP,
    STAFF_GROUP,
    SUPPORT_GROUP,
    Candidate,
    CandidateConfirmation,
    CandidateSupporter,
    CandidateVote,
    Organization,
)

register = template.Library()


@register.filter
def cant_vote(user, candidate):
    orgs = Organization.objects.filter(user=user)

    if not orgs:
        return True

    if any(org.status == "accepted" for org in orgs):
        return False
    else:
        return True


@register.filter
def can_vote_candidate(user, candidate):
    if CandidateVote.objects.filter(user=user, candidate=candidate).exists():
        return False

    votes_for_domain = CandidateVote.objects.filter(user=user, domain=candidate.domain).count()
    if votes_for_domain >= candidate.domain.seats:
        return False

    return True


@register.filter
def already_voted_candidate(user, candidate):
    if CandidateVote.objects.filter(user=user, candidate=candidate).exists():
        return True
    return False


@register.filter
def already_confirmed_candidate_status(user, candidate):
    if CandidateConfirmation.objects.filter(user=user, candidate=candidate).exists():
        return True
    return False


@register.filter
def in_committee_or_staff_groups(user):
    return user.groups.filter(name__in=[COMMITTEE_GROUP, STAFF_GROUP, SUPPORT_GROUP]).exists()


@register.simple_tag
def supporters(candidate_id):
    return CandidateSupporter.objects.filter(candidate=candidate_id).count()


@register.filter
def already_supported(user, candidate):
    if CandidateSupporter.objects.filter(user=user, candidate=candidate).exists():
        return True
    return False


@register.filter
def has_all_org_documents(user):
    org = user.orgs.first()

    if all([org.report_2019, org.report_2018, org.report_2017, org.fiscal_certificate, org.statute, org.statement]):
        return True

    return False


@register.simple_tag
def votes_per_candidate(candidate):
    return CandidateVote.objects.filter(candidate=candidate).count()


@register.filter
def candidates_in_domain(domain):
    return (
        Candidate.objects.filter(domain=domain, status="accepted", is_proposed=True)
        .annotate(votes_count=Count("votes", distinct=True))
        .order_by("-votes_count")
    )
