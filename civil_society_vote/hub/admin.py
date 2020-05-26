import csv
import io

from django.contrib import admin, messages
from django.contrib.admin.filters import AllValuesFieldListFilter
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from impersonate.admin import UserAdminImpersonateMixin

from hub.forms import ImportCitiesForm
from hub.models import COUNTIES, COUNTY_RESIDENCE, Candidate, CandidateVote, City, Organization, OrganizationVote


class ImpersonableUserAdmin(UserAdminImpersonateMixin, UserAdmin):
    open_new_window = True
    pass

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["user_id"] = object_id
        return super().change_view(request, object_id, form_url, extra_context=extra_context)


# NOTE: This is needed in order for impersonate to work
admin.site.unregister(User)
admin.site.register(User, ImpersonableUserAdmin)


class CountyFilter(AllValuesFieldListFilter):
    template = "admin/dropdown_filter.html"


class OrganizationVoteInline(admin.TabularInline):
    model = OrganizationVote
    fields = ["user", "org", "domain", "vote", "motivation"]
    readonly_fields = ["user", "org", "domain", "vote", "motivation"]
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "get_user", "representative", "city", "status", "created")
    list_filter = ("status", "domain", ("county", CountyFilter))
    search_fields = ("name", "representative", "email")
    autocomplete_fields = ["city"]
    inlines = [OrganizationVoteInline]

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
            user_url = reverse("admin:auth_user_change", args=(obj.user.id,))
            return mark_safe(f'<a href="{user_url}">{obj.user.get_full_name()}</a>')

    get_user.short_description = _("user")


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


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ("name", "org", "role", "domain", "created")
    list_filter = ("domain",)
    search_fields = ("name", "email", "org")
    inlines = [CandidateVoteInline]

    def has_add_permission(self, request, obj=None):
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
