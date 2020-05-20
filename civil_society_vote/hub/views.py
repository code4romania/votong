import json

from django.contrib.auth.models import User
from django.contrib.postgres.search import (
    SearchVector,
    TrigramSimilarity,
    SearchRank,
    SearchQuery,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _
from django.views.generic import ListView, DetailView, CreateView

from hub import utils
from hub.models import (
    ADMIN_GROUP_NAME,
    CES_GROUP_NAME,
    SGG_GROUP_NAME,
    Organization,
)
from hub.forms import OrganizationRegisterForm


class InfoContextMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        with open(f"static/data/sidebar_{translation.get_language()}.json") as info:
            context["info"] = json.loads(info.read())

        return context


class OrganizationListView(InfoContextMixin, ListView):
    allow_filters = ["county", "city"]
    paginate_by = 9
    template_name = "ngo/list.html"

    def get_orgs(self):
        return Organization.objects.filter(status="accepted")

    def search(self, queryset):
        # TODO: it should take into account selected language. Check only romanian for now.
        query = self.request.GET.get("q")
        if not query:
            return queryset

        if hasattr(self, "search_cache") and query in self.search_cache:
            return self.search_cache[query]

        search_query = SearchQuery(query, config="romanian_unaccent")

        vector = SearchVector("name", weight="A", config="romanian_unaccent") + SearchVector(
            "founders", weight="B", config="romanian_unaccent"
        )

        result = (
            queryset.annotate(
                rank=SearchRank(vector, search_query),
                similarity=(TrigramSimilarity("name", query) + TrigramSimilarity("founders", query)),
            )
            .filter(Q(rank__gte=0.3) | Q(similarity__gt=0.3))
            .order_by("name")
            .distinct("name")
        )
        if not hasattr(self, "search_cache"):
            self.search_cache = {}

        self.search_cache[query] = result

        return result

    def get_queryset(self):
        orgs = self.search(self.get_orgs())
        filters = {name: self.request.GET[name] for name in self.allow_filters if name in self.request.GET}
        return orgs.filter(**filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        orgs = self.search(self.get_orgs())

        context["current_county"] = self.request.GET.get("county")
        context["current_city"] = self.request.GET.get("city")
        context["current_search"] = self.request.GET.get("q", "")
        context["current_domain"] = self.request.GET.getlist("domain", "")
        context["counties"] = orgs.order_by("county").values_list("county", flat=True).distinct("county")

        if self.request.GET.get("county"):
            orgs = orgs.filter(county=self.request.GET.get("county"))

        context["cities"] = set(orgs.values_list("city__city", flat=True))

        return context


class OrganizationDetailView(InfoContextMixin, DetailView):
    template_name = "ngo/detail.html"
    context_object_name = "ngo"
    model = Organization


class OrganizationRegisterRequestCreateView(SuccessMessageMixin, InfoContextMixin, CreateView):
    template_name = "ngo/register_request.html"
    model = Organization
    form_class = OrganizationRegisterForm
    success_message = _(
        "Thank you for signing up! The form you filled in has reached us. Someone from the RoHelp team will reach out to you as soon as your organization is validated. If you have any further questions, e-mail us at rohelp@code4.ro"
    )

    def get_success_url(self):
        return reverse("ngos-register-request")

    def get_success_message(self, cleaned_data):
        authorized_groups = [ADMIN_GROUP_NAME, CES_GROUP_NAME, SGG_GROUP_NAME]

        for user in User.objects.filter(groups__name__in=authorized_groups):
            cleaned_data["base_path"] = f"{self.request.scheme}://{self.request.META['HTTP_HOST']}"
            utils.send_email(
                template="mail/new_ngo.html", context=cleaned_data, subject="ONG nou", to=user.email,
            )

        return super().get_success_message(cleaned_data)
