from django.conf import settings
from django.contrib.auth.mixins import AccessMixin, LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector, TrigramSimilarity
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.views.generic.base import TemplateView

from hub import utils
from hub.forms import CandidateRegisterForm, CandidateUpdateForm, OrganizationForm
from hub.models import (
    COMMITTEE_GROUP,
    VOTE,
    Candidate,
    CandidateVote,
    City,
    Domain,
    FeatureFlag,
    Organization,
    OrganizationVote,
)


class MenuMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if not self.request.user or self.request.user.is_anonymous:
            return context

        # user_org = self.request.user.orgs.first()
        # if user_org:
        #     context["user_org_candidate"] = user_org.candidate

        return context


class OrgVotersGroupRequireddMixin(AccessMixin):
    """Verify that the current user is in the org voters group or owns the organization."""

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs.get("pk")

        if pk and request.user.orgs.filter(pk=pk).exists():
            return super().dispatch(request, *args, **kwargs)

        if not request.user.groups.filter(name=COMMITTEE_GROUP).exists():
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)


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


class HubUpdateView(MenuMixin, SuccessMessageMixin, UpdateView):
    pass


class OrganizationListView(OrgVotersGroupRequireddMixin, HubListView):
    allow_filters = ["county", "city"]
    paginate_by = 9
    template_name = "ngo/list.html"

    def get_qs(self):
        return Organization.objects.all()

    def get_queryset(self):
        qs = self.search(self.get_qs())
        filters = {name: self.request.GET[name] for name in self.allow_filters if self.request.GET.get(name)}
        return qs.filter(**filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        orgs = self.search(self.get_qs())

        context["current_search"] = self.request.GET.get("q", "")
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

        return context


class OrganizationDetailView(OrgVotersGroupRequireddMixin, HubDetailView):
    template_name = "ngo/detail.html"
    context_object_name = "ngo"
    model = Organization


class OrganizationRegisterRequestCreateView(HubCreateView):
    template_name = "ngo/register_request.html"
    model = Organization
    form_class = OrganizationForm
    success_message = _(
        "Thank you for signing up! The form you filled in has reached us. Someone from our team will reach out to you "
        "as soon as your organization is validated. If you have any further questions, send us a message using the "
        "form in our contact page."
    )

    def get_success_url(self):
        return reverse("ngos-register-request")


class OrganizationUpdateView(HubUpdateView):
    template_name = "ngo/update.html"
    model = Organization
    form_class = OrganizationForm


class OrganizationVoteView(OrgVotersGroupRequireddMixin, View):
    def get(self, request, pk):
        if not FeatureFlag.objects.filter(flag="enable_org_voting", status=FeatureFlag.STATUS.on).exists():
            return HttpResponseBadRequest()

        try:
            try:
                vote = request.GET.get("vote")
                vote_choice = getattr(VOTE, str(vote).lower())
            except AttributeError:
                raise ValidationError("Invalid vote value.")

            motivation = request.GET.get("motivation", "")
            if vote_choice == VOTE.no and not motivation:
                raise ValidationError(_("You must specify a motivation if voting NO!"))

            org = Organization.objects.get(pk=pk)
            OrganizationVote.objects.create(user=request.user, org=org, vote=vote_choice, motivation=motivation)
        except Exception as exc:
            print(exc)
            return HttpResponseBadRequest()
        else:
            return HttpResponse()


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

    def get_form_kwargs(self):
        kwargs = super(CandidateRegisterRequestCreateView, self).get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class CandidateUpdateView(LoginRequiredMixin, HubUpdateView):
    template_name = "candidate/update.html"
    model = Candidate
    form_class = CandidateUpdateForm


class CandidateVoteView(LoginRequiredMixin, View):
    def get(self, request, pk):
        if not FeatureFlag.objects.filter(flag="enable_candidate_voting", status=FeatureFlag.STATUS.on).exists():
            return HttpResponseBadRequest()

        try:
            candidate = Candidate.objects.get(pk=pk)
            vote = CandidateVote.objects.create(user=request.user, candidate=candidate)
        except Exception:
            return HttpResponseBadRequest()

        if settings.VOTE_AUDIT_EMAIL:
            utils.send_email(
                template="mail/vote_audit.html",
                context={"vote": vote},
                subject="Vot candidat",
                to=settings.VOTE_AUDIT_EMAIL,
            )
        return HttpResponse()


class CityAutocomplete(View):
    def get(self, request):
        response = []
        county = request.GET.get("county")
        if county:
            cities = City.objects.filter(county__iexact=county).values_list("id", "city", named=True)
            response = [{"id": item.id, "city": item.city} for item in cities]
        return JsonResponse(response, safe=False)
