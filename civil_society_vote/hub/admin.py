import csv
import io

from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path
from django.utils.translation import ugettext_lazy as _

from .forms import OrganizationForm, ImportCitiesForm
from .models import (
    City,
    Organization,
    OrganizationVote,
    ADMIN_GROUP_NAME,
    COUNTY_RESIDENCE,
    COUNTIES,
)


class OrganizationVoteInline(admin.TabularInline):
    model = OrganizationVote
    fields = ("user", "org", "domain", "vote", "motivation")
    can_delete = False
    can_add = False
    verbose_name_plural = _("Organization votes")
    readonly_fields = ["user", "org", "domain", "vote", "motivation"]
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_per_page = 25

    list_display = ("name", "representative", "county", "city", "created")
    list_filter = ("county",)
    search_fields = ("name", "representative", "email")
    autocomplete_fields = ["city"]
    inlines = [OrganizationVoteInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        user = request.user
        if not user.groups.filter(name=ADMIN_GROUP_NAME).exists():
            return qs.filter(users__in=[user])

        return qs

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = []
        if not obj:
            return readonly_fields

        user = request.user
        if not user.groups.filter(name=ADMIN_GROUP_NAME).exists():
            readonly_fields.append("users")

        readonly_fields.extend(["county"])

        return readonly_fields


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    """ City admin page

    At this moment, only the superuser is allowed to import new cities and
    change existing ones.
    """

    list_display = ["city", "county"]
    list_filter = ["county", "is_county_residence"]
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
            return redirect(".")

        form = ImportCitiesForm()
        context = {
            "site_header": admin.site.site_header,
            "site_title": admin.site.site_title,
            "index_title": admin.site.index_title,
            "title": _("Import Cities"),
            "form": form,
        }
        return render(request, "admin/hub/city/import_cities.html", context)
