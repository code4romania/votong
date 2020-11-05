import csv
import io

from accounts.models import User
from django.contrib import admin, messages
from django.contrib.admin.filters import AllValuesFieldListFilter
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.contrib.sites.shortcuts import get_current_site
from django.db.models import Count
from django.shortcuts import redirect, render
from django.template import Context
from django.urls import path, reverse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from impersonate.admin import UserAdminImpersonateMixin

from hub import utils
from hub.forms import ImportCitiesForm
from hub.models import (
    COMMITTEE_GROUP,
    COUNTIES,
    COUNTY_RESIDENCE,
    Candidate,
    CandidateConfirmation,
    CandidateSupporter,
    CandidateVote,
    City,
    Domain,
    EmailTemplate,
    FeatureFlag,
    Organization,
)


class ImpersonableUserAdmin(UserAdminImpersonateMixin, UserAdmin):
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


# NOTE: This is needed in order for impersonate to work
# admin.site.unregister(User)
admin.site.register(User, ImpersonableUserAdmin)


class CountyFilter(AllValuesFieldListFilter):
    template = "admin/dropdown_filter.html"


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
    readonly_fields = ["user", "status_changed"]
    autocomplete_fields = ["city"]
    list_per_page = 20

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
        return (
            ("gte10", _("10 or more")),
            ("lt10", _("less than 10")),
        )

    def queryset(self, request, queryset):
        if self.value() == "lt10":
            return queryset.filter(supporters_count__lt=10)
        if self.value() == "gte10":
            return queryset.filter(supporters_count__gte=10)


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

    confirmation_link_path = reverse("candidate-detail", args=(candidate.pk,))
    confirmation_link = f"{protocol}://{current_site.domain}{confirmation_link_path}"

    utils.send_email(
        template="confirmation",
        context=Context(
            {
                "candidate": candidate.name,
                "status": Candidate.STATUS[candidate.status],
                "confirmation_link": confirmation_link,
            }
        ),
        subject=f"[VOTONG] Confirmare candidat: {candidate.name}",
        to=to_email,
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
    inlines = [CandidateConfirmationInline, CandidateSupporterInline, CandidateVoteInline]
    actions = [accept_candidates, reject_candidates, pending_candidates]
    list_per_page = 20

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            votes_count=Count("votes", distinct=True),
            supporters_count=Count("supporters", distinct=True),
            confirmations_count=Count("confirmations", distinct=True),
        )
        return queryset

    def votes_count(self, obj):
        return obj.votes_count

    votes_count.short_description = _("Votes")
    votes_count.admin_order_field = "votes_count"

    def supporters_count(self, obj):
        return obj.supporters_count

    supporters_count.short_description = _("Supporters")
    supporters_count.admin_order_field = "supporters_count"

    def confirmations_count(self, obj):
        return obj.confirmations_count

    confirmations_count.short_description = _("Confirmations")
    confirmations_count.admin_order_field = "confirmations_count"

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
    list_display = ["name", "description"]

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
    """ City admin page

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

                city = City(city=row["Localitate"], county=row["Judet"], is_county_residence=is_county_residence,)
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

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ["template"]
    readonly_fields = ["template"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False
