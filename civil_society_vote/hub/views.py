import json

from django.contrib.auth.models import User
from django.contrib.postgres.search import (
    SearchVector,
    TrigramSimilarity,
    SearchRank,
    SearchQuery,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.core import paginator
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import ListView, DetailView, CreateView

from hub import utils
from hub.models import (
    ADMIN_GROUP_NAME,
    CES_GROUP_NAME,
    SGG_GROUP_NAME,
    DOMAIN_CHOICES,
    City,
    Organization,
)
from hub.forms import OrganizationRegisterForm


class InfoContextMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        with open(f"static/data/sidebar_{translation.get_language()}.json") as info:
            context["info"] = json.loads(info.read())

        return context


class DomainFilterMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["current_domain"] = self.request.GET.get("domain")

        if not self.request.GET.get("q"):
            context["current_domain"] = context["current_domain"] or 1

        ngo = kwargs.get("ngo", context.get("ngo"))
        if not ngo:
            return context

        orgs_qs = ngo.filter(resolved_on=None)

        for domain_id in [x[0] for x in DOMAIN_CHOICES]:
            orgs_qs = orgs_qs.filter(domain=domain_id)
            paginator_obj = paginator.Paginator(orgs_qs, 5)
            page = self.request.GET.get(f"{domain_id}_page")

            # Catch invalid page numbers
            try:
                page_obj = paginator_obj.page(page)
            except (paginator.PageNotAnInteger, paginator.EmptyPage):
                page_obj = paginator_obj.page(1)

            context[f"{domain_id}_page_obj"] = page_obj

        return context


class OrganizationListView(InfoContextMixin, DomainFilterMixin, ListView):
    allow_filters = ["county", "city", "domain"]
    paginate_by = 9
    template_name = "ngo/list.html"

    def get_orgs(self):
        # return Organization.objects.filter(status="accepted")
        return Organization.objects.all()

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
        filters = {name: self.request.GET[name] for name in self.allow_filters if self.request.GET.get(name)}
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

        if self.request.GET.get("city"):
            try:
                context["current_city_name"] = City.objects.get(id=self.request.GET.get("city")).city
            except City.DoesNotExist:
                context["current_city_name"] = "-"

        context["cities"] = set(orgs.values_list("city__id", "city__city"))

        context["domains"] = DOMAIN_CHOICES

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
        "Thank you for signing up! The form you filled in has reached us. Someone from our team will reach out to you as soon as your organization is validated. If you have any further questions, e-mail us at contact@code4.ro"
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


class CityAutocomplete(View):
    def get(self, request):
        response = []
        county = request.GET.get("county")
        if county:
            cities = City.objects.filter(county__iexact=county).values_list("id", "city", named=True)
            response = [{"id": item.id, "city": item.city} for item in cities]
        return JsonResponse(response, safe=False)
