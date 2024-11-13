from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import Group as BaseGroup
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from impersonate.admin import UserAdminImpersonateMixin

from civil_society_vote.common.admin import BasePermissionsAdmin

from .models import GroupProxy, User

# Remove the default admins for User and Group
try:
    admin.site.unregister(User)
except NotRegistered:
    pass

try:
    admin.site.unregister(BaseGroup)
except NotRegistered:
    pass


@admin.register(User)
class UserAdmin(UserAdminImpersonateMixin, BasePermissionsAdmin):
    open_new_window = True

    list_display = (
        "email",
        "get_organization",
        "get_groups",
        "is_active",
        "is_ngohub_user",
        "created",
    )
    list_display_links = (
        "email",
        "is_active",
        "is_ngohub_user",
        "created",
    )
    list_filter = ("is_ngohub_user", "is_active", "is_superuser", "is_staff", "groups")

    search_fields = ("email", "first_name", "last_name")

    readonly_fields = (
        "email",
        "password",
        "organization",
        "is_ngohub_user",
        "date_joined",
        "last_login",
        "first_name",
        "last_name",
        "groups",
        "user_permissions",
    )

    fieldsets = (
        (
            _("Identification"),
            {
                "fields": (
                    "email",
                    "is_ngohub_user",
                    "organization",
                    "first_name",
                    "last_name",
                )
            },
        ),
        (
            _("Flags"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                )
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            _("Important dates"),
            {
                "fields": (
                    "date_joined",
                    "last_login",
                )
            },
        ),
    )

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["user_id"] = object_id

        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def get_organization(self, obj: User):
        if not obj:
            return "-"

        if not obj.organization:
            return "-"

        organization_url = reverse_lazy("admin:hub_organization_change", args=[obj.organization.pk])
        return mark_safe(f'<a href="{organization_url}">{obj.organization.name}</a>')

    get_organization.short_description = _("Organization")

    def get_groups(self, obj: User):
        user_groups = obj.groups.all()

        group_url = reverse_lazy("admin:accounts_user_changelist")
        groups_display = [
            f'<a href="{group_url}?groups__id__exact={group.pk}">{group.name}</a>' for group in user_groups
        ]

        # noinspection DjangoSafeString
        return mark_safe(", ".join(groups_display))

    get_groups.short_description = _("Groups")


@admin.register(GroupProxy)
class GroupAdmin(BaseGroupAdmin, BasePermissionsAdmin): ...
