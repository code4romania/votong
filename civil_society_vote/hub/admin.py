from admin_auto_filters.filters import AutocompleteFilter

from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Count
from django.shortcuts import render
from django.template.defaultfilters import pluralize
from django.utils.html import format_html
from django.utils.translation import activate
from django.utils.translation import ugettext_lazy as _

from hub import utils

from .forms import RegisterNGORequestVoteForm, NGOForm
from .models import (
    NGO,
    RegisterNGORequest,
    PendingRegisterNGORequest,
    RegisterNGORequestVote,
    ADMIN_GROUP_NAME,
    NGO_GROUP_NAME,
    DSU_GROUP_NAME,
    FFC_GROUP_NAME,
)


class NGOFilter(AutocompleteFilter):
    title = "NGO"
    field_name = "ngo"


@admin.register(NGO)
class NGOAdmin(admin.ModelAdmin):
    icon_name = "home_work"
    list_per_page = 25
    form = NGOForm

    list_display = ("name", "contact_name", "county", "city", "created")
    list_filter = (
        "city",
        "county",
    )
    search_fields = ("name", "email")

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        user = request.user
        if not user.groups.filter(name=ADMIN_GROUP_NAME).exists():
            return qs.filter(users__in=[user])

        return qs

    def get_readonly_fields(self, request, obj=None):
        if not obj:
            return []

        user = request.user
        if not user.groups.filter(name=ADMIN_GROUP_NAME).exists():
            return ["users"]

        return []

    @transaction.atomic
    def save_model(self, request, ngo, form, change):
        super().save_model(request, ngo, form, change)


class RegisterNGORequestVoteInline(admin.TabularInline):
    model = RegisterNGORequestVote
    fields = ("entity", "vote", "motivation")
    can_delete = False
    can_add = False
    verbose_name_plural = _("Votes")
    readonly_fields = ["entity", "vote", "motivation"]
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(RegisterNGORequest)
class RegisterNGORequestAdmin(admin.ModelAdmin):
    icon_name = "add_circle"
    fields = (
        "name",
        "description",
        "past_actions",
        "resource_types",
        "contact_name",
        "email",
        "contact_phone",
        "address",
        "city",
        "county",
        "social_link",
        "active",
        "resolved_on",
        "get_logo",
        "logo",
    )
    list_display = [
        "name",
        "county",
        "city",
        "voters",
        "yes",
        "no",
        "abstention",
        "votes_count",
        "active",
        "registered_on",
        "resolved_on",
        "get_last_balance_sheet",
        "get_statute",
    ]
    actions = ["create_account", "close_request"]
    readonly_fields = ["active", "resolved_on", "registered_on", "get_logo"]
    list_filter = ("city", "county", "registered_on", "closed")
    inlines = [RegisterNGORequestVoteInline]
    search_fields = ("name",)

    def votes_count(self, obj):
        return obj.votes_count

    votes_count.admin_order_field = "votes_count"
    votes_count.short_description = _("Votes Count")

    def get_queryset(self, request):
        return self.model.objects.annotate(votes_count=Count("votes")).order_by(
            "-votes_count"
        )

    def get_changeform_initial_data(self, request):
        user = request.user
        if not user.groups.filter(name=ADMIN_GROUP_NAME).exists():
            return {"user": user.pk}

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "Admin" not in request.user.groups.values_list("name", flat=True):
            del actions["create_account"]
            del actions["close_request"]
        return actions

    def changelist_view(self, request, extra_context=None):
        q = request.GET.copy()
        if "closed__exact" not in request.GET.keys():
            q["closed__exact"] = "0"
        request.GET = q
        request.META["QUERY_STRING"] = request.GET.urlencode()
        return super().changelist_view(request, extra_context=extra_context)

    def get_last_balance_sheet(self, obj):
        if obj.last_balance_sheet:
            return format_html(
                f"<a class='' href='{obj.last_balance_sheet.url}'>{_('Open')}</a>"
            )
        return "-"

    get_last_balance_sheet.short_description = _("Last balance")

    def get_statute(self, obj):
        if obj.statute:
            return format_html(f"<a class='' href='{obj.statute.url}'>{_('Open')}</a>")
        return "-"

    get_statute.short_description = _("Statute")

    def get_logo(self, obj):
        if obj.logo:
            return format_html(f"<img src='{obj.logo.url}' width='200'>")
        return "-"

    get_logo.short_description = _("logo Preview")

    def voters(self, obj):
        return ",".join(obj.votes.values_list("entity", flat=True))

    voters.short_description = _("Voters")

    def create_account(self, request, queryset):
        ngo_group = Group.objects.get(name=NGO_GROUP_NAME)

        for register_request in queryset:
            register_request.activate(request, ngo_group)

        user_msg = f"{queryset.count()} ngo{pluralize(queryset.count(), 's')} activated"
        return self.message_user(request, user_msg, level=messages.INFO)

    create_account.short_description = _("Create account")

    def close_request(self, request, queryset):

        for register_request in queryset:
            register_request.closed = True
            register_request.save()

        user_msg = (
            f"{queryset.count()} request{pluralize(queryset.count(), 's')} closed"
        )
        return self.message_user(request, user_msg, level=messages.INFO)

    close_request.short_description = _("Close aplication")


@admin.register(PendingRegisterNGORequest)
class PendingRegisterNGORequestAdmin(admin.ModelAdmin):
    icon_name = "restore"
    list_display = [
        "name",
        "county",
        "city",
        "registered_on",
        "get_last_balance_sheet",
        "get_statute",
    ]
    fields = (
        "name",
        "description",
        "past_actions",
        "resource_types",
        "contact_name",
        "email",
        "contact_phone",
        "address",
        "city",
        "county",
        "social_link",
        "active",
        "resolved_on",
        "get_logo",
    )
    list_filter = ("city", "county", "registered_on")
    readonly_fields = ["get_logo", "resolved_on"]
    search_fields = ("name",)
    actions = ["vote"]
    inlines = [RegisterNGORequestVoteInline]

    def has_add_permission(self, request, obj=None):
        return False

    def get_last_balance_sheet(self, obj):
        if obj.last_balance_sheet:
            return format_html(
                f"<a class='' href='{obj.last_balance_sheet.url}'>{_('Open')}</a>"
            )
        return "-"

    get_last_balance_sheet.short_description = _("Last balance")

    def get_statute(self, obj):
        if obj.statute:
            return format_html(f"<a class='' href='{obj.statute.url}'>{_('Open')}</a>")
        return "-"

    get_statute.short_description = _("Statute")

    def get_logo(self, obj):
        if obj.logo:
            return format_html(f"<img src='{obj.logo.url}' width='200'>")
        return "-"

    get_logo.short_description = "logo"

    def vote(self, request, queryset):
        activate(request.LANGUAGE_CODE)
        if request.POST.get("post") == "yes":
            authorized_groups = [ADMIN_GROUP_NAME, DSU_GROUP_NAME, FFC_GROUP_NAME]
            user = request.user
            base_path = f"{request.scheme}://{request.META['HTTP_HOST']}"
            user_groups = user.groups.values_list("name", flat=True)
            entity = list(set(authorized_groups).intersection(user_groups))[0]

            for ngo_request in queryset:
                vote = RegisterNGORequestVote.objects.create(
                    user=user,
                    ngo_request=ngo_request,
                    entity=entity,
                    vote=request.POST.get("vote"),
                    motivation=request.POST.get("motivation"),
                )

                notify_groups = list(set(authorized_groups) - set(user_groups))
                e = 0
                for group in Group.objects.filter(name__in=notify_groups):
                    for user in group.user_set.all():
                        e += utils.send_email(
                            template="mail/new_vote.html",
                            context={
                                "vote": vote,
                                "user": user,
                                "base_path": base_path,
                            },
                            subject=f"[RO HELP] {entity} a votat pentru {ngo_request.name}",
                            to=user.email,
                        )
                self.message_user(
                    request,
                    _(
                        "Vote succesfully registered. {} email{} sent to others admins".format(
                            e, pluralize(e, str(_("s")))
                        )
                    ),
                    level=messages.INFO,
                )
        else:
            context = dict(
                title=f"Vot ONG",
                opts=self.model._meta,
                queryset=queryset,
                form=RegisterNGORequestVoteForm,
                action_checkbox_name=helpers.ACTION_CHECKBOX_NAME,
            )
            return render(request, "admin/vote_motivation.html", context)

    vote.short_description = _("Vote NGO")

    def get_queryset(self, request):
        user = request.user
        user_groups = user.groups.values_list("name", flat=True)
        return self.model.objects.exclude(votes__entity__in=user_groups)

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(RegisterNGORequestVote)
class RegisterNGORequestVoteAdmin(admin.ModelAdmin):
    icon_name = "how_to_vote"
    list_display = ["ngo_request", "user", "entity", "vote", "motivation", "date"]
    search_fields = ["ngo_request__name"]
    list_filter = ["user", "entity", "vote", "date"]

    def get_queryset(self, request):
        user = request.user

        if not user.groups.filter(name=ADMIN_GROUP_NAME).exists():
            user_groups = user.groups.values_list("name", flat=True)
            return self.model.objects.filter(entity__in=user_groups)

        return self.model.objects.all()

    def has_change_permission(self, request, obj=None):
        return False

    def get_changeform_initial_data(self, request):
        user = request.user
        if not user.groups.filter(name=ADMIN_GROUP_NAME).exists():
            return {"user": user.pk}
