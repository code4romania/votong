import csv
import io
from typing import List, Set

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.filters import AllValuesFieldListFilter
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth.models import Group
from django.contrib.sites.shortcuts import get_current_site
from django.db.models import Count, QuerySet
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from sentry_sdk import capture_message

from accounts.models import COMMITTEE_GROUP, User
from civil_society_vote.common.admin import BasePermissionsAdmin
from civil_society_vote.common.messaging import send_email
from hub.forms import ImportCitiesForm, OrganizationCreateFromNgohubForm
from hub.models import (
    BlogPost,
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
    PHASE_CHOICES,
    SETTINGS_CHOICES,
    get_feature_flag,
)
from hub.workers.update_organization import update_organization


class CountyFilter(AllValuesFieldListFilter):
    template = "admin/dropdown_filter.html"


class OrganizationUsersInline(admin.TabularInline):
    model = User
    fields = ["email", "first_name", "last_name", "is_active", "is_staff", "is_superuser", "groups"]
    readonly_fields = ["email", "first_name", "last_name"]
    show_change_link = True

    extra = 0

    def has_view_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class OrganizationCandidatesInline(admin.TabularInline):
    model = Candidate
    fields = ["name", "status", "is_proposed", "votes_count", "supporters_count", "confirmations_count"]
    readonly_fields = fields
    show_change_link = True
    fk_name = "org"

    extra = 0

    def has_view_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def votes_count(self, obj):
        return obj.count_votes()

    votes_count.short_description = _("Votes")

    def supporters_count(self, obj):
        return obj.count_supporters()

    supporters_count.short_description = _("Supporters")

    def confirmations_count(self, obj):
        return obj.count_confirmations()

    confirmations_count.short_description = _("Confirmations")


class CandidateVoteInline(admin.TabularInline):
    model = CandidateVote
    fields = ["user", "organization", "candidate"]
    readonly_fields = ["user", "organization", "candidate", "domain"]
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
        if get_feature_flag(SETTINGS_CHOICES.global_support_round):
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


def _set_candidates_status(
    request: HttpRequest,
    queryset: QuerySet[Candidate],
    status: str,
    send_committee_confirmation: bool = True,
):
    committee_emails = Group.objects.get(name=COMMITTEE_GROUP).user_set.all().values_list("email", flat=True)

    for candidate in queryset:
        # only take action if there is a change in the status
        if candidate.status != status:
            CandidateConfirmation.objects.filter(candidate=candidate).delete()

            if not send_committee_confirmation:
                continue

            for to_email in committee_emails:
                send_confirm_email_to_committee(request, candidate, to_email)

    queryset.update(status=status)


def reject_candidates(_, request: HttpRequest, queryset: QuerySet[Candidate]):
    _set_candidates_status(request, queryset, Candidate.STATUS.rejected)


reject_candidates.short_description = _("Set selected candidates status to REJECTED")


def accept_candidates(_, request: HttpRequest, queryset: QuerySet[Candidate]):
    _set_candidates_status(request, queryset, Candidate.STATUS.accepted)


accept_candidates.short_description = _("Set selected candidates status to ACCEPTED")


def pending_candidates(_, request: HttpRequest, queryset: QuerySet[Candidate]):
    _set_candidates_status(request, queryset, Candidate.STATUS.pending, send_committee_confirmation=False)


pending_candidates.short_description = _("Set selected candidates status to PENDING")


class DomainResource(resources.ModelResource):
    class Meta:
        model = Domain
        fields = ["id", "name", "seats", "description"]
        import_id_fields = ["id"]


@admin.register(Organization)
class OrganizationAdmin(BasePermissionsAdmin):
    list_display = (
        "name",
        "get_user",
        "get_candidate",
        "city",
        "get_voting_domain",
        "status",
        "created",
    )
    list_display_links = (
        "name",
        "city",
        "status",
        "created",
    )
    list_filter = ("status", ("county", CountyFilter), "voting_domain")

    search_fields = ("name", "legal_representative_name", "email")
    readonly_fields = ["ngohub_org_id"] + list(Organization.ngohub_fields())
    autocomplete_fields = ["city"]
    list_per_page = 20

    inlines = (OrganizationUsersInline, OrganizationCandidatesInline)

    actions = ("update_organizations",)

    fieldsets = (
        (
            _("Identification"),
            {
                "fields": (
                    "status",
                    "ngohub_org_id",
                    "voting_domain",
                )
            },
        ),
        (
            _("Contact Information"),
            {
                "fields": (
                    "email",
                    "phone",
                    "name",
                    "county",
                    "city",
                    "address",
                    "registration_number",
                    "board_council",
                    "logo",
                    "description",
                    "activity_summary",
                )
            },
        ),
        (
            _("Legal representative"),
            {
                "fields": (
                    "legal_representative_name",
                    "legal_representative_email",
                    "legal_representative_phone",
                )
            },
        ),
        (
            _("Platform documents"),
            {
                "fields": (
                    "last_balance_sheet",
                    "statute",
                    "statement_political",
                    "statement_discrimination",
                    "fiscal_certificate_anaf",
                    "fiscal_certificate_local",
                    "report_2023",
                    "report_2022",
                    "report_2021",
                )
            },
        ),
    )

    def has_change_permission(self, request, obj=None):
        if request.user.is_staff:
            return True
        return False

    def get_user(self, obj: Organization = None):
        if obj and obj.users.exists():
            org_user = obj.users.first()
            user_url = reverse("admin:accounts_user_change", args=(org_user.id,))
            return mark_safe(f'<a href="{user_url}">{org_user.email}</a>')

    get_user.short_description = _("user")

    def get_candidate(self, obj=None):
        if obj and obj.candidate:
            user_url = reverse("admin:hub_candidate_change", args=(obj.candidate.id,))
            return mark_safe(f'<a href="{user_url}">{obj.candidate.name}</a>')

    get_candidate.short_description = _("candidate")

    def get_voting_domain(self, obj: Organization):
        if obj and obj.voting_domain:
            domain_url = (
                reverse("admin:hub_organization_changelist")
                + "?"
                + urlencode({"voting_domain__id__exact": obj.voting_domain.pk})
            )
            return mark_safe(f'<a href="{domain_url}">{obj.voting_domain.name}</a>')

        return _("Not set")

    get_voting_domain.short_description = _("voting domain")

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.ngohub_org_id:
            readonly_fields = ["ngohub_org_id"] + list(Organization.ngohub_fields())
            if not request.user.is_superuser:
                readonly_fields.extend(
                    [
                        "status",
                        "voting_domain",
                    ]
                )

            return readonly_fields

        return []

    def get_form(self, request, obj=None, **kwargs):
        admin_user = request.user
        if not obj and not kwargs["change"] and admin_user.is_superuser:
            kwargs["fields"] = list(OrganizationCreateFromNgohubForm().fields.keys())
            return OrganizationCreateFromNgohubForm

        return super().get_form(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        if not obj and request.user.is_superuser:
            return (
                (
                    _("Identification"),
                    {
                        "fields": (
                            "ngohub_org_id",
                            "user_id",
                        )
                    },
                ),
            )

        return self.fieldsets

    def get_inlines(self, request, obj=None):
        if not obj and request.user.is_superuser:
            return []

        return self.inlines

    @staticmethod
    def update_organizations(__, ___, queryset):
        for org in queryset:
            update_organization(org.id)


@admin.register(Candidate)
class CandidateAdmin(BasePermissionsAdmin):
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
    list_display_links = list_display

    list_filter = ["is_proposed", "status", CandidateSupportersListFilter, CandidateConfirmationsListFilter, "domain"]
    search_fields = ["name", "org__name"]
    readonly_fields = ["status"]
    actions = [accept_candidates, reject_candidates, pending_candidates]
    list_per_page = 20

    fieldsets = (
        (
            _("Status Information"),
            {
                "fields": (
                    "status",
                    "org",
                    "initial_org",
                    "domain",
                    "is_proposed",
                )
            },
        ),
        (
            _("Candidate Information"),
            {
                "fields": (
                    "name",
                    "role",
                    "photo",
                ),
            },
        ),
        (
            _("Candidate Files"),
            {
                "fields": (
                    "statement",
                    "mandate",
                    "letter_of_intent",
                    "cv",
                    "declaration_of_interests",
                    "fiscal_record",
                    "criminal_record",
                ),
            },
        ),
    )

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

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = self.readonly_fields

        if request.user.is_superuser:
            return readonly_fields

        readonly_fields.extend(["org", "initial_org", "domain", "is_proposed", "name", "role"])

        return readonly_fields

    def get_inline_instances(self, request, obj=None):
        if get_feature_flag(SETTINGS_CHOICES.global_support_round):
            inlines = [CandidateConfirmationInline, CandidateSupporterInline, CandidateVoteInline]
        else:
            inlines = [CandidateConfirmationInline, CandidateVoteInline]
        return [inline(self.model, self.admin_site) for inline in inlines]

    def votes_count(self, obj):
        return obj.votes.count()

    votes_count.short_description = _("Votes")

    def supporters_count(self, obj):
        if get_feature_flag(SETTINGS_CHOICES.global_support_round):
            return obj.count_supporters()
        else:
            return "N/A"

    supporters_count.short_description = _("Supporters")

    def confirmations_count(self, obj):
        return obj.confirmations.count()

    confirmations_count.short_description = _("Confirmations")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_staff:
            return True
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Domain)
class DomainAdmin(ImportExportModelAdmin, BasePermissionsAdmin):
    list_display_links = list_display = ("id", "name", "seats", "description")
    ordering = ("id",)
    resource_class = DomainResource


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

    def has_view_permission(self, request, obj=None):
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
class FeatureFlagAdmin(BasePermissionsAdmin):
    list_display = ["flag", "is_enabled"]
    readonly_fields = ["flag"]
    actions = [
        "enable_flags",
        "disable_flags",
        "flags_phase_pause",
        "flags_phase_deactivate",
        "flags_phase_1",
        "flags_phase_2",
        "flags_phase_3",
        "flags_final_phase",
    ]

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

    def enable_flags(self, request, queryset):
        queryset.update(is_enabled=True)

    enable_flags.short_description = _("Activate selected flags")

    def disable_flags(self, request, queryset):
        queryset.update(is_enabled=False)

    disable_flags.short_description = _("Deactivate selected flags")

    def _flags_switch_phase(self, request, phase_name: str, enabled: List[str], disabled: List[str]):
        phase_choices: Set[str] = set([flag[0] for flag in PHASE_CHOICES])

        all_flags_in_model: Set[str] = set([flag[0] for flag in FLAG_CHOICES])
        all_flags_in_database: Set[str] = set(FeatureFlag.objects.values_list("flag", flat=True))
        if invalid_flags := all_flags_in_model.difference(all_flags_in_database):
            missing_flags: str = ", ".join(invalid_flags)
            error_message: str = _(f"Configuration invalid. Missing flag(s) in database: {missing_flags}.")

            self.message_user(request, message=error_message, level=messages.WARNING)

            if settings.ENABLE_SENTRY:
                capture_message(error_message, level="warning")

            return

        full_list: Set[str] = set(enabled + disabled)
        if invalid_flags := phase_choices.difference(full_list):
            missing_flags: str = ", ".join(invalid_flags)
            error_message: str = _(f"'{phase_name}' configuration invalid. Missing flag(s): {missing_flags}.")

            self.message_user(request, message=error_message, level=messages.ERROR)

            if settings.ENABLE_SENTRY:
                capture_message(error_message, level="error")

            return

        FeatureFlag.objects.filter(flag__in=enabled).update(is_enabled=True)
        FeatureFlag.objects.filter(flag__in=disabled).update(is_enabled=False)
        FeatureFlag.delete_cache()

        if "enable_candidate_supporting" in enabled:
            FeatureFlag.objects.filter(flag=PHASE_CHOICES.enable_candidate_supporting).update(
                is_enabled=get_feature_flag(SETTINGS_CHOICES.global_support_round)
            )

        self.message_user(request, message=_(f"Flags set successfully for '{phase_name}'."), level=messages.SUCCESS)

    def flags_phase_pause(self, request, __: QuerySet[FeatureFlag]):
        self._flags_switch_phase(
            request=request,
            phase_name=_("PHASE PAUSE - platform pause"),
            enabled=[
                "enable_org_registration",
                "enable_org_editing",
                "enable_org_approval",
            ],
            disabled=[
                "enable_candidate_registration",
                "enable_candidate_editing",
                "enable_candidate_supporting",
                "enable_candidate_confirmation",
                "enable_candidate_voting",
                "enable_results_display",
            ],
        )

    flags_phase_pause.short_description = _("Set flags for PHASE PAUSE - platform pause")

    def flags_phase_deactivate(self, request, __: QuerySet[FeatureFlag]):
        self._flags_switch_phase(
            request=request,
            phase_name=_("PHASE DEACTIVATE - platform deactivate"),
            enabled=[],
            disabled=[
                "enable_org_registration",
                "enable_org_editing",
                "enable_org_approval",
                "enable_candidate_registration",
                "enable_candidate_editing",
                "enable_candidate_supporting",
                "enable_candidate_confirmation",
                "enable_candidate_voting",
                "enable_results_display",
            ],
        )

    flags_phase_deactivate.short_description = _("Set flags for PHASE - platform deactivate")

    def flags_phase_1(self, request, __: QuerySet[FeatureFlag]):
        self._flags_switch_phase(
            request=request,
            phase_name=_("PHASE 1 - organization & candidate registrations"),
            enabled=[
                "enable_org_registration",
                "enable_org_editing",
                "enable_org_approval",
                "enable_candidate_registration",
                "enable_candidate_editing",
                "enable_candidate_supporting",
            ],
            disabled=[
                "enable_candidate_confirmation",
                "enable_candidate_voting",
                "enable_results_display",
            ],
        )

    flags_phase_1.short_description = _("Set flags for PHASE 1 - organization & candidate registrations")

    def flags_phase_2(self, request, __: QuerySet[FeatureFlag]):
        self._flags_switch_phase(
            request=request,
            phase_name=_("PHASE 2 - candidate validation"),
            enabled=[
                "enable_org_registration",
                "enable_org_editing",
                "enable_org_approval",
                "enable_candidate_confirmation",
            ],
            disabled=[
                "enable_candidate_registration",
                "enable_candidate_editing",
                "enable_candidate_supporting",
                "enable_candidate_voting",
                "enable_results_display",
            ],
        )

    flags_phase_2.short_description = _("Set flags for PHASE 2 - candidate validation")

    def flags_phase_3(self, request, __: QuerySet[FeatureFlag]):
        self._flags_switch_phase(
            request=request,
            phase_name=_("PHASE 3 - voting"),
            enabled=[
                "enable_org_registration",
                "enable_org_editing",
                "enable_org_approval",
                "enable_candidate_voting",
            ],
            disabled=[
                "enable_candidate_registration",
                "enable_candidate_editing",
                "enable_candidate_supporting",
                "enable_results_display",
                "enable_candidate_confirmation",
            ],
        )

    flags_phase_3.short_description = _("Set flags for PHASE 3 - voting")

    def flags_final_phase(self, request, __: QuerySet[FeatureFlag]):
        self._flags_switch_phase(
            request=request,
            phase_name=_("FINAL PHASE - results"),
            enabled=[
                "enable_results_display",
            ],
            disabled=[
                "enable_org_registration",
                "enable_org_editing",
                "enable_org_approval",
                "enable_candidate_registration",
                "enable_candidate_editing",
                "enable_candidate_supporting",
                "enable_candidate_voting",
                "enable_candidate_confirmation",
            ],
        )

    flags_final_phase.short_description = _("Set flags for FINAL PHASE - results")


@admin.register(BlogPost)
class BlogPostAdmin(BasePermissionsAdmin):
    list_display = ["title", "slug", "author", "published_date", "is_visible"]

    def has_add_permission(self, request, obj=None):
        if request.user.is_staff:
            return True
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_staff:
            return True
        return False
