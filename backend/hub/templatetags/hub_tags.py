from django import template
from django.utils import timezone
from django.utils.translation import gettext as _

from accounts.models import User
from hub.models import (
    COMMITTEE_GROUP,
    STAFF_GROUP,
    SUPPORT_GROUP,
    CandidateConfirmation,
    CandidateSupporter,
    CandidateVote,
    Organization,
)

register = template.Library()


@register.filter
def can_vote(user):
    if Organization.objects.filter(user=user, status=Organization.STATUS.accepted).count():
        return True
    return False


@register.filter
def can_vote_candidate(user, candidate):
    if CandidateVote.objects.filter(user=user, candidate=candidate).exists():
        return False

    votes_for_domain = CandidateVote.objects.filter(user=user, domain=candidate.domain).count()
    if votes_for_domain >= candidate.domain.seats:
        return False

    return True


@register.filter
def can_support_candidate(user):
    if Organization.objects.filter(user=user, status=Organization.STATUS.accepted).count():
        return True
    return False


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


@register.filter
def in_commission_group(user):
    return (
        user.groups.filter(name=COMMITTEE_GROUP).exists()
        and not user.groups.filter(name__in=[STAFF_GROUP, SUPPORT_GROUP]).exists()
    )


@register.filter
def in_staff_groups(user):
    return user.groups.filter(name__in=[STAFF_GROUP, SUPPORT_GROUP]).exists()


@register.filter
def already_supported(user, candidate):
    if CandidateSupporter.objects.filter(user=user, candidate=candidate).exists():
        return True
    return False


@register.filter
def has_all_org_documents(user):
    return user.orgs.first().is_complete()


@register.simple_tag
def show_blog_post_date_prefix(published_date):
    today = timezone.now().date()
    delta = today - published_date

    if delta.days > 1:
        return _("published on")

    return _("published")


@register.filter
def has_permission(user: User, permission: str) -> bool:
    user_groups = user.groups.all()
    user_group_has_perm = any([group.permissions.filter(codename=permission).exists() for group in user_groups])

    user_has_perm = user.has_perm(permission)

    return user_group_has_perm or user_has_perm
