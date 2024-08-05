from django import template
from django.utils import timezone
from django.utils.translation import gettext as _

from accounts.models import User
from hub.models import CandidateConfirmation, Organization

register = template.Library()


@register.filter
def can_vote(user):
    if Organization.objects.filter(user=user, status=Organization.STATUS.accepted).count():
        return True
    return False


@register.filter
def already_confirmed_candidate_status(user, candidate):
    if CandidateConfirmation.objects.filter(user=user, candidate=candidate).exists():
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
