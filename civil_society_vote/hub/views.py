from django.conf import settings
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector, TrigramSimilarity
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.views.generic.base import TemplateView
from guardian.decorators import permission_required_or_403
from guardian.mixins import LoginRequiredMixin, PermissionListMixin, PermissionRequiredMixin

from hub import utils
from hub.forms import CandidateRegisterForm, CandidateUpdateForm, OrganizationForm
from hub.models import Candidate, CandidateVote, City, Domain, FeatureFlag, Organization


class MenuMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if not self.request.user or self.request.user.is_anonymous:
            return context

        # user_org = self.request.user.orgs.first()
        # if user_org:
        #     context["user_org_candidate"] = user_org.candidate

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


class HubUpdateView(MenuMixin, SuccessMessageMixin, UpdateView):
    pass


class CommitteeOrganizationListView(LoginRequiredMixin, PermissionListMixin, HubListView):
    permission_required = "hub.approve_organization"
    raise_exception = True
    paginate_by = 9
    template_name = "committee/list.html"

    def get_queryset(self):
        return Organization.objects.filter(status=Organization.STATUS.pending)


class OrganizationListView(HubListView):
    allow_filters = ["county", "city"]
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


class OrganizationDetailView(HubDetailView):
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

    def get(self, request, *args, **kwargs):
        if not FeatureFlag.objects.filter(flag="enable_org_registration", is_enabled=True).exists():
            raise PermissionDenied
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not FeatureFlag.objects.filter(flag="enable_org_registration", is_enabled=True).exists():
            raise PermissionDenied
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("ngos-register-request")


class OrganizationUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HubUpdateView):
    permission_required = "hub.change_organization"
    raise_exception = True
    template_name = "ngo/update.html"
    model = Organization
    form_class = OrganizationForm


@permission_required_or_403("hub.approve_organization", (Organization, "pk", "pk"))
def organization_vote(request, pk, action):
    if not FeatureFlag.objects.filter(flag="enable_org_approval", is_enabled=True).exists():
        raise PermissionDenied

    try:
        org = Organization.objects.get(pk=pk, status=Organization.STATUS.pending)
    except Organization.DoesNotExist:
        pass
    else:
        if action == "r":
            org.status = Organization.STATUS.rejected
        elif action == "a":
            org.status = Organization.STATUS.accepted
        org.save()
    finally:
        return redirect("ngo-detail", pk=pk)


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

    def get(self, request, *args, **kwargs):
        if not FeatureFlag.objects.filter(flag="enable_candidate_registration", is_enabled=True).exists():
            raise PermissionDenied
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not FeatureFlag.objects.filter(flag="enable_candidate_registration", is_enabled=True).exists():
            raise PermissionDenied
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(CandidateRegisterRequestCreateView, self).get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class CandidateUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HubUpdateView):
    permission_required = "hub.change_candidate"
    raise_exception = True
    template_name = "candidate/update.html"
    model = Candidate
    form_class = CandidateUpdateForm


class CandidateVoteView(LoginRequiredMixin, View):
    def get(self, request, pk):
        if not FeatureFlag.objects.filter(flag="enable_candidate_voting", is_enabled=True).exists():
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
