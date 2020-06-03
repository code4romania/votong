from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector, TrigramSimilarity
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import CreateView, DetailView, ListView
from django.views.generic.base import TemplateView

from hub import utils
from hub.forms import CandidateRegisterForm, OrganizationRegisterForm
from hub.models import ADMIN_GROUP_NAME, CES_GROUP_NAME, SGG_GROUP_NAME, Candidate, City, Domain, Organization


class MenuMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if not self.request.user or self.request.user.is_anonymous:
            return context

        user_org = self.request.user.orgs.first()
        if user_org:
            context["user_org_candidate"] = user_org.candidate

        return context


class HomeView(MenuMixin, TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # TODO: Add needed context here
        return context


class HubListView(MenuMixin, ListView):
    def search(self, queryset):
        # TODO: it should take into account selected language. Check only romanian for now.
        query = self.request.GET.get("q")
        if not query:
            return queryset

        if hasattr(self, "search_cache") and query in self.search_cache:
            return self.search_cache[query]

        search_query = SearchQuery(query, config="romanian_unaccent")

        vector = SearchVector("name", weight="A", config="romanian_unaccent")

        result = (
            queryset.annotate(rank=SearchRank(vector, search_query), similarity=TrigramSimilarity("name", query),)
            .filter(Q(rank__gte=0.3) | Q(similarity__gt=0.3))
            .order_by("name")
            .distinct("name")
        )
        if not hasattr(self, "search_cache"):
            self.search_cache = {}

        self.search_cache[query] = result

        return result


class HubDetailView(MenuMixin, DetailView):
    pass


class HubCreateView(MenuMixin, SuccessMessageMixin, CreateView):
    pass


class OrganizationListView(HubListView):
    allow_filters = ["county", "city", "domain"]
    paginate_by = 9
    template_name = "ngo/list.html"

    def get_qs(self):
        return Organization.objects.filter(status=Organization.STATUS.accepted)

    def get_queryset(self):
        qs = self.search(self.get_qs())
        filters = {name: self.request.GET[name] for name in self.allow_filters if self.request.GET.get(name)}
        return qs.filter(**filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        orgs = self.search(self.get_qs())

        context["current_search"] = self.request.GET.get("q", "")

        current_domain = self.request.GET.get("domain")
        if current_domain:
            try:
                context["current_domain"] = Domain.objects.get(id=current_domain)
            except Domain.DoesNotExist:
                pass

        context["current_county"] = self.request.GET.get("county")
        context["current_city"] = self.request.GET.get("city")
        context["counties"] = orgs.order_by("county").values_list("county", flat=True).distinct("county")

        if self.request.GET.get("county"):
            orgs = orgs.filter(county=self.request.GET.get("county"))

        if self.request.GET.get("city"):
            try:
                context["current_city_name"] = City.objects.get(id=self.request.GET.get("city")).city
            except City.DoesNotExist:
                context["current_city_name"] = "-"

        context["cities"] = set(orgs.values_list("city__id", "city__city"))

        context["domains"] = Domain.objects.all()

        return context


class OrganizationDetailView(HubDetailView):
    template_name = "ngo/detail.html"
    context_object_name = "ngo"
    model = Organization


class OrganizationRegisterRequestCreateView(HubCreateView):
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


class CandidateListView(HubListView):
    allow_filters = ["domain"]
    paginate_by = 9
    template_name = "candidate/list.html"

    def get_qs(self):
        return Candidate.objects.filter(org__status=Organization.STATUS.accepted)

    def get_queryset(self):
        qs = self.search(self.get_qs())
        filters = {name: self.request.GET[name] for name in self.allow_filters if self.request.GET.get(name)}
        return qs.filter(**filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_search"] = self.request.GET.get("q", "")

        current_domain = self.request.GET.get("domain")
        if current_domain:
            try:
                context["current_domain"] = Domain.objects.get(id=current_domain)
            except Domain.DoesNotExist:
                pass

        context["domains"] = Domain.objects.all()
        return context


class CandidateDetailView(HubDetailView):
    template_name = "candidate/detail.html"
    context_object_name = "candidate"
    model = Candidate


class CandidateRegisterRequestCreateView(LoginRequiredMixin, HubCreateView):
    template_name = "candidate/register_request.html"
    model = Candidate
    form_class = CandidateRegisterForm
    success_message = _("Thank you for signing up your candidate!")

    def get_success_url(self):
        return reverse("candidate-register-request")

    def get_form_kwargs(self):
        kwargs = super(CandidateRegisterRequestCreateView, self).get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    # def get_success_message(self, cleaned_data):
    #     authorized_groups = [ADMIN_GROUP_NAME, CES_GROUP_NAME, SGG_GROUP_NAME]

    #     for user in User.objects.filter(groups__name__in=authorized_groups):
    #         cleaned_data["base_path"] = f"{self.request.scheme}://{self.request.META['HTTP_HOST']}"
    #         utils.send_email(
    #             template="mail/new_candidate.html", context=cleaned_data, subject=_("New candidate"), to=user.email,
    #         )

    #     return super().get_success_message(cleaned_data)
