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
    DSU_GROUP_NAME,
    FFC_GROUP_NAME,
    NGO,
    RegisterNGORequest,
)
from hub.forms import NGORegisterRequestForm


class InfoContextMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        with open(f"static/data/sidebar_{translation.get_language()}.json") as info:
            context["info"] = json.loads(info.read())

        return context


class NGOListView(InfoContextMixin, ListView):

    allow_filters = ["county", "city", "urgency"]
    paginate_by = 9

    template_name = "ngo/list.html"

    def get_needs(self):
        return NGO.objects.all()

    def search(self, queryset):
        # TODO: it should take into account selected language. Check only romanian for now.
        query = self.request.GET.get("q")
        if not query:
            return queryset

        if hasattr(self, "search_cache") and query in self.search_cache:
            return self.search_cache[query]

        search_query = SearchQuery(query, config="romanian_unaccent")

        vector = SearchVector(
            "title", weight="A", config="romanian_unaccent"
        ) + SearchVector("ngo__name", weight="B", config="romanian_unaccent")

        result = (
            queryset.annotate(
                rank=SearchRank(vector, search_query),
                similarity=(
                    TrigramSimilarity("title", query)
                    + TrigramSimilarity("ngo__name", query)  # noqa
                ),
            )
            .filter(Q(rank__gte=0.3) | Q(similarity__gt=0.3))
            .order_by("title", "-rank")
            .distinct("title")
        )
        if not hasattr(self, "search_cache"):
            self.search_cache = {}

        self.search_cache[query] = result

        return result

    def get_queryset(self):
        needs = self.search(self.get_needs())
        filters = {
            name: self.request.GET[name]
            for name in self.allow_filters
            if name in self.request.GET
        }
        return needs.filter(**filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        needs = self.search(self.get_needs())

        context["current_county"] = self.request.GET.get("county")
        context["current_city"] = self.request.GET.get("city")
        context["current_urgency"] = self.request.GET.get("urgency")
        context["current_search"] = self.request.GET.get("q", "")
        context["current_tags"] = self.request.GET.getlist("tag", "")
        context["counties"] = (
            needs.order_by("county").values_list("county", flat=True).distinct("county")
        )

        if self.request.GET.get("county"):
            needs = needs.filter(county=self.request.GET.get("county"))

        context["cities"] = set(needs.values_list("city", flat=True))
        context["urgencies"] = []

        return context


class NGODetailView(InfoContextMixin, DetailView):
    template_name = "ngo/detail.html"
    context_object_name = "ngo"
    model = NGO


class NGORegisterRequestCreateView(SuccessMessageMixin, InfoContextMixin, CreateView):
    template_name = "ngo/register_request.html"
    model = RegisterNGORequest
    form_class = NGORegisterRequestForm
    success_message = _(
        "Thank you for signing up! The form you filled in has reached us. Someone from the RoHelp team will reach out to you as soon as your organization is validated. If you have any further questions, e-mail us at rohelp@code4.ro"
    )

    def get_success_url(self):
        return reverse("ngos-register-request")

    def get_success_message(self, cleaned_data):
        authorized_groups = [ADMIN_GROUP_NAME, DSU_GROUP_NAME, FFC_GROUP_NAME]

        for user in User.objects.filter(groups__name__in=authorized_groups):
            cleaned_data[
                "base_path"
            ] = f"{self.request.scheme}://{self.request.META['HTTP_HOST']}"
            utils.send_email(
                template="mail/new_ngo.html",
                context=cleaned_data,
                subject="[RO HELP] ONG nou",
                to=user.email,
            )

        return super().get_success_message(cleaned_data)
