from urllib.parse import unquote

from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector, TrigramSimilarity
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template import Context
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import CreateView, DetailView, FormView, ListView, UpdateView
from guardian.decorators import permission_required_or_403
from guardian.mixins import LoginRequiredMixin, PermissionRequiredMixin

from hub import utils
from hub.forms import (
    CandidateRegisterForm,
    CandidateUpdateForm,
    ContactForm,
    OrganizationCreateForm,
    OrganizationUpdateForm,
)
from hub.models import (
    COMMITTEE_GROUP,
    STAFF_GROUP,
    Candidate,
    CandidateSupporter,
    CandidateVote,
    City,
    Domain,
    FeatureFlag,
    Organization,
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


class HomeView(MenuMixin, SuccessMessageMixin, FormView):
    template_name = "home.html"
    form_class = ContactForm
    success_url = "/#contact"
    success_message = _("Thank you! We'll get in touch soon!")

    def form_valid(self, form):
        form.send_email()
        return super().form_valid(form)


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


class CommitteeOrganizationListView(LoginRequiredMixin, HubListView):
    allow_filters = ["status"]
    paginate_by = 9
    template_name = "committee/list.html"

    def get_queryset(self):
        if not self.request.user.groups.filter(name__in=[COMMITTEE_GROUP, STAFF_GROUP]).exists():
            raise PermissionDenied

        filters = {name: self.request.GET[name] for name in self.allow_filters if self.request.GET.get(name)}

        if not filters:
            return Organization.objects.filter(status=Organization.STATUS.pending).order_by("-created")

        return Organization.objects.filter(**filters).order_by("-created")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filtering"] = "ngos-" + self.request.GET.get("status", Organization.STATUS.pending)
        context["counters"] = {
            "ngos_pending": Organization.objects.filter(status=Organization.STATUS.pending).count(),
            "ngos_accepted": Organization.objects.filter(status=Organization.STATUS.accepted).count(),
            "ngos_rejected": Organization.objects.filter(status=Organization.STATUS.rejected).count(),
            "candidates_pending": Candidate.objects_with_org.filter(status=Candidate.STATUS.pending).count(),
            "candidates_accepted": Candidate.objects_with_org.filter(status=Candidate.STATUS.accepted).count(),
        }
        return context


class CommitteeCandidatesListView(LoginRequiredMixin, HubListView):
    allow_filters = ["status"]
    paginate_by = 9
    template_name = "committee/candidates.html"

    def get_queryset(self):
        if not self.request.user.groups.filter(name__in=[COMMITTEE_GROUP, STAFF_GROUP]).exists():
            raise PermissionDenied

        filters = {name: self.request.GET[name] for name in self.allow_filters if self.request.GET.get(name)}
        return (
            Candidate.objects_with_org.filter(**filters)
            .annotate(supporters_count=Count("supporters"))
            .order_by("-supporters_count")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filtering"] = self.request.GET.get("status", Candidate.STATUS.pending)
        context["counters"] = {
            "ngos_pending": Organization.objects.filter(status=Organization.STATUS.pending).count(),
            "ngos_accepted": Organization.objects.filter(status=Organization.STATUS.accepted).count(),
            "ngos_rejected": Organization.objects.filter(status=Organization.STATUS.rejected).count(),
            "candidates_pending": Candidate.objects_with_org.filter(status=Candidate.STATUS.pending).count(),
            "candidates_accepted": Candidate.objects_with_org.filter(status=Candidate.STATUS.accepted).count(),
        }
        return context


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

    def get_queryset(self):
        if self.request.user.groups.filter(name__in=[COMMITTEE_GROUP, STAFF_GROUP]).exists():
            return Organization.objects.all()

        return Organization.objects.filter(status=Organization.STATUS.accepted)


class OrganizationRegisterRequestCreateView(HubCreateView):
    template_name = "ngo/register_request.html"
    model = Organization
    form_class = OrganizationCreateForm
    success_message = _(
        "Thank you for signing up! The form you filled in has reached us. Someone from our team will reach out to you "
        "as soon as your organization is validated. If you have any further questions, send us a message at contact@votong.ro"
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
    form_class = OrganizationUpdateForm

    def get_success_url(self):
        return reverse("ngo-update", args=(self.object.id,))


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
            org.rejection_message = unquote(request.GET.get("rejection-message", ""))
            org.status = Organization.STATUS.rejected

            if org.rejection_message:
                org.save()
                utils.send_email(
                    template="org_rejected",
                    context=Context(
                        {
                            "representative": org.legal_representative_name,
                            "name": org.name,
                            "rejection_message": org.rejection_message,
                        }
                    ),
                    subject="Cerere de inscriere respinsa",
                    to=org.email,
                )
            else:
                messages.error(request, _("You must write a rejection message."))
        elif action == "a":
            org.status = Organization.STATUS.accepted
            org.save()
            current_site = get_current_site(request)
            protocol = "https" if request.is_secure() else "http"
            utils.send_email(
                template="org_approved",
                context=Context(
                    {
                        "representative": org.legal_representative_name,
                        "name": org.name,
                        "reset_url": f"{protocol}://{current_site.domain}{reverse('password_reset')}",
                    }
                ),
                subject="Cerere de inscriere aprobata",
                to=org.email,
            )
    finally:
        return redirect("ngo-detail", pk=pk)


class CandidateListView(HubListView):
    allow_filters = ["domain"]
    paginate_by = 9
    template_name = "candidate/list.html"

    def get_qs(self):
        if not FeatureFlag.objects.filter(flag="enable_candidate_voting", is_enabled=True).exists():
            return Candidate.objects_with_org.filter(
                org__status=Organization.STATUS.accepted, status=Candidate.STATUS.pending, is_proposed=True
            )

        return Candidate.objects_with_org.filter(
            org__status=Organization.STATUS.accepted, status=Candidate.STATUS.accepted, is_proposed=True
        )

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

    def get_queryset(self):
        if self.request.user.groups.filter(name__in=[COMMITTEE_GROUP, STAFF_GROUP]).exists():
            return Candidate.objects_with_org.all()

        if not FeatureFlag.objects.filter(flag="enable_candidate_voting", is_enabled=True).exists():
            return Candidate.objects_with_org.filter(
                org__status=Organization.STATUS.accepted, status=Candidate.STATUS.pending, is_proposed=True
            )

        return Candidate.objects_with_org.filter(
            org__status=Organization.STATUS.accepted, status=Candidate.STATUS.accepted, is_proposed=True
        )


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

    def get_success_url(self):
        return reverse("candidate-update", args=(self.object.id,))


class CandidateUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HubUpdateView):
    permission_required = "hub.change_candidate"
    raise_exception = True
    template_name = "candidate/update.html"
    model = Candidate
    form_class = CandidateUpdateForm

    def get_success_url(self):
        return reverse("candidate-update", args=(self.object.id,))

    def post(self, request, *args, **kwargs):
        if not FeatureFlag.objects.filter(flag="enable_candidate_registration", is_enabled=True).exists():
            raise PermissionDenied
        return super().post(request, *args, **kwargs)


class CandidateVoteView(LoginRequiredMixin, View):
    def get(self, request, pk):
        if not FeatureFlag.objects.filter(flag="enable_candidate_voting", is_enabled=True).exists():
            return HttpResponseBadRequest()

        try:
            candidate = Candidate.objects.get(
                pk=pk, org__status=Organization.STATUS.accepted, status=Candidate.STATUS.accepted, is_proposed=True
            )
            vote = CandidateVote.objects.create(user=request.user, candidate=candidate)
        except Exception:
            return HttpResponseBadRequest()

        if settings.VOTE_AUDIT_EMAIL:
            current_site = get_current_site(request)
            protocol = "https" if request.is_secure() else "http"
            utils.send_email(
                template="vote_audit",
                context=Context(
                    {
                        "org": vote.user.orgs.first().name,
                        "candidate": vote.candidate.name,
                        "timestamp": vote.created.isoformat(),
                        "org_link": f"{protocol}://{current_site.domain}{vote.user.orgs.first().get_absolute_url()}",
                        "candidate_link": f"{protocol}://{current_site.domain}{vote.candidate.get_absolute_url()}",
                    }
                ),
                subject=f"[VOTONG] Vot candidat: {vote.candidate.name}",
                to=settings.VOTE_AUDIT_EMAIL,
            )
        return HttpResponse()


@permission_required_or_403("hub.delete_candidate", (Candidate, "pk", "pk"))
def revoke_candidate(request, pk):
    if not FeatureFlag.objects.filter(flag="enable_candidate_registration", is_enabled=True).exists():
        raise PermissionDenied

    candidate = get_object_or_404(Candidate, pk=pk)

    if candidate.org != request.user.orgs.first():
        return redirect("candidate-detail", pk=pk)

    with transaction.atomic():
        candidate.supporters.all().delete()
        candidate.initial_org = candidate.org
        candidate.save()

    return redirect("candidate-register-request")


@permission_required_or_403("hub.support_candidate", (Candidate, "pk", "pk"))
def candidate_support(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)

    if candidate.org == request.user.orgs.first():
        return redirect("candidate-detail", pk=pk)

    try:
        supporter = CandidateSupporter.objects.get(user=request.user, candidate=candidate)
    except CandidateSupporter.DoesNotExist:
        CandidateSupporter.objects.create(user=request.user, candidate=candidate)
    else:
        supporter.delete()

    return redirect("candidate-detail", pk=pk)


class CityAutocomplete(View):
    def get(self, request):
        response = []
        county = request.GET.get("county")
        if county:
            cities = City.objects.filter(county__iexact=county).values_list("id", "city", named=True)
            response = [{"id": item.id, "city": item.city} for item in cities]
        return JsonResponse(response, safe=False)
