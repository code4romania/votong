from django import template

from hub.models import COMMITTEE_GROUP, STAFF_GROUP, CandidateConfirmation, CandidateSupporter, CandidateVote

register = template.Library()


@register.filter
def already_voted_candidate_or_domain(user, candidate):
    if CandidateVote.objects.filter(user=user, candidate=candidate).exists():
        return True

    if CandidateVote.objects.filter(user=user, domain=candidate.domain).exists():
        return True

    return False


@register.filter
def already_confirmed_candidate_status(user, candidate):
    if CandidateConfirmation.objects.filter(user=user, candidate=candidate).exists():
        return True
    return False


@register.filter
def in_committee_or_staff_group(user):
    return user.groups.filter(name__in=[COMMITTEE_GROUP, STAFF_GROUP]).exists()


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
