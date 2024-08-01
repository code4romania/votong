import csv
import io
from typing import List, Set

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.filters import AllValuesFieldListFilter
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.contrib.sites.shortcuts import get_current_site
from django.db.models import Count
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from impersonate.admin import UserAdminImpersonateMixin
from sentry_sdk import capture_message

from accounts.models import User
from civil_society_vote.common.messaging import send_email
from hub.forms import ImportCitiesForm
from hub.models import (
    BlogPost,
    COMMITTEE_GROUP,
    COUNTIES,
    COUNTY_RESIDENCE,
    Candidate,
    CandidateConfirmation,
    CandidateSupporter,
    CandidateVote,
    City,
    Domain,
    FLAG_CHOICES,
    FeatureFlag,
    Organization,
    get_feature_flag,
)
from hub.workers.update_organization import update_organization


class NoUsernameUserAdmin(UserAdmin):
    """
    UserAdmin without the `username` field
    """

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )


class ImpersonableUserAdmin(UserAdminImpersonateMixin, NoUsernameUserAdmin):
    list_display = ("email", "get_groups", "is_active", "is_staff", "is_superuser")
    open_new_window = True
    pass

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["user_id"] = object_id
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def get_groups(self, obj=None):
        if obj:
            groups = obj.groups.all().values_list("name", flat=True)
            return ", ".join(groups)

    get_groups.short_description = _("groups")


# NOTE: This is needed in order for impersonation to work
# admin.site.unregister(User)
admin.site.register(User, ImpersonableUserAdmin)


class CountyFilter(AllValuesFieldListFilter):
    template = "admin/dropdown_filter.html"


def update_organizations(modeladmin, request, queryset):
    for org in queryset:
        update_organization(org.id)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "get_user",
        "get_candidate",
        "city",
        "legal_representative_name",
        "status",
        "created",
    )
    list_filter = ("status", ("county", CountyFilter))
    search_fields = ("name", "legal_representative_name", "email")
    readonly_fields = ["status_changed"]
    autocomplete_fields = ["city"]
    list_per_page = 20

    actions = (update_organizations,)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False

    def get_user(self, obj=None):
        if obj and obj.user:
            user_url = reverse("admin:accounts_user_change", args=(obj.user.id,))
            return mark_safe(f'<a href="{user_url}">{obj.user.email}</a>')

    get_user.short_description = _("user")

    def get_candidate(self, obj=None):
        if obj and obj.candidate:
            user_url = reverse("admin:hub_candidate_change", args=(obj.candidate.id,))
            return mark_safe(f'<a href="{user_url}">{obj.candidate.name}</a>')

    get_candidate.short_description = _("candidate")


class CandidateVoteInline(admin.TabularInline):
    model = CandidateVote
    fields = ["user", "candidate"]
    readonly_fields = ["user", "candidate", "domain"]
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CandidateSupporterInline(admin.TabularInline):
    model = CandidateSupporter
    fields = ["user", "candidate"]
    readonly_fields = ["user", "candidate"]
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CandidateConfirmationInline(admin.TabularInline):
    model = CandidateConfirmation
    fields = ["user", "candidate"]
    readonly_fields = ["user", "candidate"]
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CandidateSupportersListFilter(admin.SimpleListFilter):
    title = _("supporters")
    parameter_name = "supporters"

    def lookups(self, request, model_admin):
        if get_feature_flag(FLAG_CHOICES.global_support_round):
            return (
                ("gte10", _("10 or more")),
                ("lt10", _("less than 10")),
            )
        return

    def queryset(self, request, queryset):
        if self.value() == "lt10":
            return queryset.annotate(supporters_count=Count("supporters")).filter(supporters_count__lt=10)
        if self.value() == "gte10":
            return queryset.annotate(supporters_count=Count("supporters")).filter(supporters_count__gte=10)


class CandidateConfirmationsListFilter(admin.SimpleListFilter):
    title = _("confirmations")
    parameter_name = "confirmations"

    def lookups(self, request, model_admin):
        return (
            ("gte5", _("5 or more")),
            ("lt5", _("less than 5")),
        )

    def queryset(self, request, queryset):
        if self.value() == "lt5":
            return queryset.filter(confirmations_count__lt=5)
        if self.value() == "gte5":
            return queryset.filter(confirmations_count__gte=5)


def send_confirm_email_to_committee(request, candidate, to_email):
    current_site = get_current_site(request)
    protocol = "https" if request.is_secure() else "http"

    confirmation_link_path = reverse("candidate-status-confirm", args=(candidate.pk,))
    confirmation_link = f"{protocol}://{current_site.domain}{confirmation_link_path}"

    send_email(
        subject=f"[VOTONG] Confirmare candidatura: {candidate.name}",
        context={
            "candidate": candidate.name,
            "status": Candidate.STATUS[candidate.status],
            "confirmation_link": confirmation_link,
        },
        to_emails=[to_email],
        text_template="hub/emails/05_confirmation.txt",
        html_template="hub/emails/05_confirmation.html",
    )


def reject_candidates(modeladmin, request, queryset):
    committee_emails = Group.objects.get(name=COMMITTEE_GROUP).user_set.all().values_list("email", flat=True)

    for candidate in queryset:
        # only take action if there is a chance in the status
        if candidate.status != Candidate.STATUS.rejected:
            CandidateConfirmation.objects.filter(candidate=candidate).delete()
            for to_email in committee_emails:
                send_confirm_email_to_committee(request, candidate, to_email)

    queryset.update(status=Candidate.STATUS.rejected)


reject_candidates.short_description = _("Set selected candidates status to REJECTED")


def accept_candidates(modeladmin, request, queryset):
    committee_emails = Group.objects.get(name=COMMITTEE_GROUP).user_set.all().values_list("email", flat=True)

    for candidate in queryset:
        # only take action if there is a chance in the status
        if candidate.status != Candidate.STATUS.accepted:
            CandidateConfirmation.objects.filter(candidate=candidate).delete()
            for to_email in committee_emails:
                send_confirm_email_to_committee(request, candidate, to_email)

    queryset.update(status=Candidate.STATUS.accepted)


accept_candidates.short_description = _("Set selected candidates status to ACCEPTED")


def pending_candidates(modeladmin, request, queryset):
    for candidate in queryset:
        # only take action if there is a chance in the status
        if candidate.status != Candidate.STATUS.pending:
            CandidateConfirmation.objects.filter(candidate=candidate).delete()

    queryset.update(status=Candidate.STATUS.pending)


pending_candidates.short_description = _("Set selected candidates status to PENDING")


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "org",
        "domain",
        "is_proposed",
        "status",
        "supporters_count",
        "confirmations_count",
        "votes_count",
        "created",
    ]
    list_filter = ["is_proposed", "status", CandidateSupportersListFilter, CandidateConfirmationsListFilter, "domain"]
    search_fields = ["name", "email", "org__name"]
    readonly_fields = ["status", "status_changed"]
    actions = [accept_candidates, reject_candidates, pending_candidates]
    list_per_page = 20

    # def get_queryset(self, request):
    #     queryset = super().get_queryset(request)
    #     if get_feature_flag(FLAG_CHOICES.global_support_round):
    #         queryset = queryset.annotate(
    #             votes_count=Count("votes", distinct=True),
    #             supporters_count=Count("supporters", distinct=True),
    #             confirmations_count=Count("confirmations", distinct=True),
    #         )
    #     else:
    #         queryset = queryset.annotate(
    #             votes_count=Count("votes", distinct=True),
    #             confirmations_count=Count("confirmations", distinct=True),
    #         )
    #     return queryset

    def get_inline_instances(self, request, obj=None):
        if get_feature_flag(FLAG_CHOICES.global_support_round):
            inlines = [CandidateConfirmationInline, CandidateSupporterInline, CandidateVoteInline]
        else:
            inlines = [CandidateConfirmationInline, CandidateVoteInline]
        return [inline(self.model, self.admin_site) for inline in inlines]

    def votes_count(self, obj):
        return obj.votes.count()

    votes_count.short_description = _("Votes")
    # votes_count.admin_order_field = "votes_count"

    def supporters_count(self, obj):
        if get_feature_flag(FLAG_CHOICES.global_support_round):
            return obj.count_supporters()
        else:
            return "N/A"

    supporters_count.short_description = _("Supporters")
    # supporters_count.admin_order_field = "supporters_count"

    def confirmations_count(self, obj):
        return obj.confirmations.count()

    confirmations_count.short_description = _("Confirmations")
    # confirmations_count.admin_order_field = "confirmations_count"

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ["name", "seats", "description"]

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        return False

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    """City admin page

    At this moment, only the superuser is allowed to import new cities and
    change existing ones.
    """

    list_display = ["city", "county"]
    list_filter = ["is_county_residence", ("county", CountyFilter)]
    search_fields = ["city"]
    list_per_page = 20

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("import-cities/", self.import_cities, name="import_cities"),
        ]
        return custom_urls + urls

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False

    def import_cities(self, request):
        if request.method == "POST":
            form = ImportCitiesForm(request.POST, request.FILES)
            if not form.is_valid():
                self.message_user(request, f"[ERROR] {form.errors.as_text()}", level=messages.ERROR)
                return redirect(".")

            csv_file = io.StringIO(request.FILES["csv_file"].read().decode("utf-8"))
            reader = csv.DictReader(csv_file)

            batch_size = 1000
            batch = []

            for row in reader:
                if row["Judet"] not in COUNTIES:
                    continue

                is_county_residence = False
                if (row["Judet"], row["Localitate"]) in COUNTY_RESIDENCE:
                    is_county_residence = True

                city = City(
                    city=row["Localitate"],
                    county=row["Judet"],
                    is_county_residence=is_county_residence,
                )
                batch.append(city)

                if len(batch) == batch_size:
                    City.objects.bulk_create(batch, batch_size=batch_size, ignore_conflicts=True)
                    batch = []

            # Create the remaining items in the batch
            if len(batch):
                City.objects.bulk_create(batch, batch_size=len(batch), ignore_conflicts=True)

            self.message_user(request, _("CSV file imported"), level=messages.INFO)
            return redirect("..")

        form = ImportCitiesForm()
        context = {
            "site_header": admin.site.site_header,
            "site_title": admin.site.site_title,
            "index_title": admin.site.index_title,
            "title": _("Import Cities"),
            "form": form,
        }
        return render(request, "admin/hub/city/import_cities.html", context)


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ["flag", "is_enabled"]
    readonly_fields = ["flag"]
    actions = ["flags_phase_1", "flags_phase_2", "flags_phase_3", "flags_final_phase"]

    def changelist_view(self, request, extra_context=None):
        if "action" in request.POST:
            if not request.POST.getlist(ACTION_CHECKBOX_NAME):
                post = request.POST.copy()
                for ff in FeatureFlag.objects.all():
                    post.update({ACTION_CHECKBOX_NAME: str(ff.pk)})
                request._set_post(post)

        return super(FeatureFlagAdmin, self).changelist_view(request, extra_context)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False

    def _flags_switch_phase(self, request, phase_name: str, enabled: List[str], disabled: List[str]):
        all_flag_choices: Set[str] = {
            "enable_org_registration",
            "enable_org_approval",
            "enable_org_voting",
            "enable_candidate_registration",
            "enable_candidate_supporting",
            "enable_candidate_confirmation",
            "enable_candidate_voting",
            "enable_results_display",
        }

        global_flag_choices: Set[str] = {flag[0] for flag in FLAG_CHOICES}
        if len(invalid_flags := global_flag_choices.symmetric_difference(all_flag_choices)) != 2:
            missing_flags = ", ".join(invalid_flags.difference(global_flag_choices))
            error_message: str = _(f"Invalid flag choices: {missing_flags} not found in {global_flag_choices}.")

            self.message_user(request, message=error_message, level=messages.ERROR)

            if settings.ENABLE_SENTRY:
                capture_message(error_message, level="error")

            return

        full_list: Set[str] = set(enabled + disabled)
        if invalid_flags := all_flag_choices.difference(full_list):
            missing_flags: str = ", ".join(invalid_flags)
            error_message: str = _(f"'{phase_name}' configuration invalid. Missing flag(s): {missing_flags}.")

            self.message_user(request, message=error_message, level=messages.ERROR)

            if settings.ENABLE_SENTRY:
                capture_message(error_message, level="error")

            return

        FeatureFlag.objects.filter(flag__in=enabled).update(is_enabled=True)
        FeatureFlag.objects.filter(flag__in=disabled).update(is_enabled=False)

        if "enable_candidate_supporting" in enabled:
            FeatureFlag.objects.filter(flag="enable_candidate_supporting").update(
                is_enabled=get_feature_flag(FLAG_CHOICES.global_support_round)
            )

        self.message_user(request, message=_(f"Flags set successfully for '{phase_name}'."), level=messages.SUCCESS)

    def flags_phase_1(self, request, queryset):
        self._flags_switch_phase(
            request=request,
            phase_name=_("PHASE 1 - organization & candidate registrations"),
            enabled=[
                "enable_org_registration",
                "enable_org_approval",
                "enable_org_voting",
                "enable_candidate_registration",
                "enable_candidate_supporting",
            ],
            disabled=[
                "enable_candidate_confirmation",
                "enable_candidate_voting",
                "enable_results_display",
            ],
        )

    flags_phase_1.short_description = _("Set flags for PHASE 1 - organization & candidate registrations")

    def flags_phase_2(self, request, queryset):
        self._flags_switch_phase(
            request=request,
            phase_name=_("PHASE 2 - candidate validation"),
            enabled=[
                "enable_org_registration",
                "enable_org_approval",
                "enable_org_voting",
                "enable_candidate_confirmation",
            ],
            disabled=[
                "enable_candidate_registration",
                "enable_candidate_supporting",
                "enable_candidate_voting",
                "enable_results_display",
            ],
        )

    flags_phase_2.short_description = _("Set flags for PHASE 2 - candidate validation")

    def flags_phase_3(self, request, queryset):
        self._flags_switch_phase(
            request=request,
            phase_name=_("PHASE 3 - voting"),
            enabled=[
                "enable_org_registration",
                "enable_org_approval",
                "enable_org_voting",
                "enable_candidate_voting",
            ],
            disabled=[
                "enable_candidate_registration",
                "enable_candidate_supporting",
                "enable_results_display",
                "enable_candidate_confirmation",
            ],
        )

    flags_phase_3.short_description = _("Set flags for PHASE 3 - voting")

    def flags_final_phase(self, request, queryset):
        self._flags_switch_phase(
            request=request,
            phase_name=_("FINAL PHASE - results"),
            enabled=[
                "enable_results_display",
                "enable_org_registration",
                "enable_org_approval",
                "enable_org_voting",
            ],
            disabled=[
                "enable_candidate_registration",
                "enable_candidate_supporting",
                "enable_candidate_voting",
            ],
        )

    flags_final_phase.short_description = _("Set flags for FINAL PHASE - results")


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ["title", "slug", "author", "published_date", "is_visible"]

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        return False

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False
