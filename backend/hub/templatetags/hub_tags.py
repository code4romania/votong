from django import template
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _

from accounts.models import User
from hub.models import CandidateConfirmation, Organization

register = template.Library()


@register.filter
def can_vote(user):
    if Organization.objects.filter(users=user, status=Organization.STATUS.accepted).count():
        return True
    return False


@register.filter
def already_confirmed_candidate_status(user, candidate):
    if CandidateConfirmation.objects.filter(user=user, candidate=candidate).exists():
        return True
    return False


@register.filter
def has_all_org_documents(user):
    return user.organization.is_complete()


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


@register.simple_tag
def org_logo(user, width=settings.AVATAR_DEFAULT_SIZE, height=None, **kwargs):
    if height is None:
        height = width

    if not user:
        return ""

    org = user.organization
    logo_url = settings.AVATAR_DEFAULT_URL
    if org and org.logo:
        logo_url = org.logo.url

    kwargs["aria-label"] = "Avatar"

    context = {
        "user": user,
        "url": logo_url,
        "alt": str(org),
        "width": width,
        "height": height,
        "kwargs": kwargs,
    }
    template_name = "avatar/avatar_tag.html"

    return render_to_string(template_name, context)


# taken from templatetags/allauth.py
@register.tag(name="set_var")
def do_setvar(parser, token):
    nodelist = parser.parse(("end_set_var",))
    bits = token.split_contents()
    if len(bits) != 2:
        tag_name = bits[0]
        usage = f'{{% {tag_name} "set_var" var %}} ... {{% end_{tag_name} %}}'
        raise template.TemplateSyntaxError("Usage: %s" % usage)
    parser.delete_first_token()
    return SetVarNode(nodelist, bits[1])


class SetVarNode(template.Node):
    def __init__(self, nodelist, var):
        self.nodelist = nodelist
        self.var = var

    def render(self, context):
        context[self.var] = self.nodelist.render(context).strip()
        return ""
