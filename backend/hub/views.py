import logging
from datetime import datetime
from urllib.parse import unquote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector, TrigramSimilarity
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.db.utils import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import CreateView, DetailView, FormView, ListView, UpdateView
from guardian.decorators import permission_required_or_403
from guardian.mixins import LoginRequiredMixin, PermissionRequiredMixin
from sentry_sdk import capture_message

from accounts.models import COMMITTEE_GROUP, NGO_GROUP, STAFF_GROUP, SUPPORT_GROUP, User
from civil_society_vote.common.messaging import send_email
from hub.forms import (
    CandidateRegisterForm,
    CandidateUpdateForm,
    ContactForm,
    OrganizationCreateForm,
    OrganizationUpdateForm,
)
from hub.models import (
    BlogPost,
    Candidate,
    CandidateConfirmation,
    CandidateSupporter,
    CandidateVote,
    City,
    Domain,
    FLAG_CHOICES,
    FeatureFlag,
    Organization,
)
from hub.workers.update_organization import update_organization

logger = logging.getLogger(__name__)


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
    template_name = "hub/home.html"
    form_class = ContactForm
    success_url = "/#contact"
    success_message = _("Thank you! We'll get in touch soon!")

    def form_valid(self, form):
        form.send_form_email()
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
            queryset.annotate(
                rank=SearchRank(vector, search_query),
                similarity=TrigramSimilarity("name", query),
            )
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
    template_name = "hub/committee/list.html"

    def get_queryset(self):
        if not self.request.user.groups.filter(name__in=[COMMITTEE_GROUP, STAFF_GROUP, SUPPORT_GROUP]).exists():
            raise PermissionDenied

        filters = {name: self.request.GET[name] for name in self.allow_filters if self.request.GET.get(name)}

        if not filters:
            return Organization.objects.filter(status=Organization.STATUS.pending).order_by("-created")

        return Organization.objects.filter(**filters).order_by("-created")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filtering"] = "ngos-" + self.request.GET.get("status", Organization.STATUS.pending)
        context["counters"] = _get_candidates_counters()
        return context


def _get_candidates_counters():
    return {
        "ngos_pending": Organization.objects.filter(status=Organization.STATUS.pending).count(),
        "ngos_accepted": Organization.objects.filter(status=Organization.STATUS.accepted).count(),
        "ngos_rejected": Organization.objects.filter(status=Organization.STATUS.rejected).count(),
        "candidates_pending": Candidate.objects_with_org.filter(status=Candidate.STATUS.pending).count(),
        "candidates_accepted": Candidate.objects_with_org.filter(status=Candidate.STATUS.accepted).count(),
        "candidates_confirmed": Candidate.objects_with_org.filter(status=Candidate.STATUS.confirmed).count(),
        "candidates_rejected": Candidate.objects_with_org.filter(status=Candidate.STATUS.rejected).count(),
    }


class CommitteeCandidatesListView(LoginRequiredMixin, HubListView):
    allow_filters = ["status"]
    paginate_by = 9
    template_name = "hub/committee/candidates.html"

    def get_queryset(self):
        if not self.request.user.groups.filter(name__in=[COMMITTEE_GROUP, STAFF_GROUP, SUPPORT_GROUP]).exists():
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
        context["counters"] = _get_candidates_counters()
        return context


class ElectorCandidatesListView(LoginRequiredMixin, HubListView):
    allow_filters = ["status"]
    paginate_by = 9
    template_name = "hub/ngo/votes.html"

    def get_queryset(self):
        if not self.request.user.groups.filter(name__in=[NGO_GROUP]).exists():
            raise PermissionDenied

        voted_candidates = CandidateVote.objects.filter(user=self.request.user)
        return [element.candidate for element in voted_candidates]


class OrganizationListView(HubListView):
    allow_filters = ["county", "city"]
    paginate_by = 9
    template_name = "hub/ngo/list.html"

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)

        if self.request.GET.get("q"):
            response["X-Robots-Tag"] = "noindex"

        return response

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
        context["counters"] = {
            "ngos_accepted": Organization.objects.filter(status=Organization.STATUS.accepted).count(),
        }

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
    template_name = "hub/ngo/detail.html"
    context_object_name = "ngo"
    model = Organization

    def get_queryset(self):
        user = self.request.user

        if org_pk := self.kwargs.get("pk"):
            if user.is_authenticated and user.orgs.exists() and user.orgs.first().pk == org_pk:
                return Organization.objects.filter(pk=org_pk)
            return Organization.objects.filter(pk=org_pk, status=Organization.STATUS.accepted)

        return Organization.objects.filter(status=Organization.STATUS.accepted)


class OrganizationRegisterRequestCreateView(HubCreateView):
    template_name = "hub/ngo/register_request.html"
    model = Organization
    form_class = OrganizationCreateForm
    success_message = _(
        "Thank you for signing up! The form you filled in has reached us. Someone from our team will reach out to you "
        "as soon as your organization is validated. If you have any further questions, send us a message at contact@votong.ro"
    )

    def get(self, request, *args, **kwargs):
        if not settings.ENABLE_ORG_REGISTRATION_FORM or not FeatureFlag.flag_enabled("enable_org_registration"):
            raise PermissionDenied
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not settings.ENABLE_ORG_REGISTRATION_FORM or not FeatureFlag.flag_enabled("enable_org_registration"):
            raise PermissionDenied
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("ngos-register-request")


class OrganizationUpdateView(LoginRequiredMixin, PermissionRequiredMixin, HubUpdateView):
    permission_required = "hub.change_organization"
    raise_exception = True
    template_name = "hub/ngo/update.html"
    model = Organization
    form_class = OrganizationUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        organization: Organization = self.object
        context["update_status"] = "is-success" if organization.status == "accepted" else "is-warning"

        return context

    def get_success_url(self):
        return reverse("ngo-update", args=(self.object.id,))

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@permission_required_or_403("hub.approve_organization")
def organization_vote(request, pk, action):
    if not FeatureFlag.flag_enabled("enable_org_approval"):
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
                send_email(
                    subject="Cerere de înscriere respinsă",
                    to_emails=[org.email],
                    text_template="hub/emails/03_org_rejected.txt",
                    html_template="hub/emails/03_org_rejected.html",
                    context={
                        "representative": org.legal_representative_name,
                        "name": org.name,
                        "rejection_message": org.rejection_message,
                    },
                )
            else:
                messages.error(request, _("You must write a rejection message."))
        elif action == "a":
            try:
                org.status = Organization.STATUS.accepted
                org.save()
            except IntegrityError as exc:
                if 'duplicate key value violates unique constraint "accounts_user_email_key"' in str(exc):
                    messages.error(request, _("An organization with the same email address is already registered."))

            current_site = get_current_site(request)
            protocol = "https" if request.is_secure() else "http"
            send_email(
                subject="Cerere de înscriere aprobată",
                to_emails=[org.email],
                text_template="hub/emails/02_org_approved.txt",
                html_template="hub/emails/02_org_approved.html",
                context={
                    "representative": org.legal_representative_name,
                    "name": org.name,
                    "site_url": f"{protocol}://{current_site.domain}",
                },
            )
    finally:
        return redirect("ngo-detail", pk=pk)


class CandidateListView(HubListView):
    allow_filters = ["domain"]
    paginate_by = 9
    template_name = "hub/candidate/list.html"

    def get_winners(self):
        # TODO: Display the winners of the election
        #   return the candidates in the order of votes with a limit per domain
        return Candidate.objects_with_org.filter(
            org__status=Organization.STATUS.accepted,
            status=Candidate.STATUS.accepted,
            is_proposed=True,
        )

    def get_qs(self):
        if FeatureFlag.flag_enabled("enable_candidate_voting"):
            return Candidate.objects_with_org.filter(
                org__status=Organization.STATUS.accepted,
                status=Candidate.STATUS.confirmed,
                is_proposed=True,
            )
        elif FeatureFlag.flag_enabled("enable_candidate_supporting"):
            return Candidate.objects_with_org.filter(
                org__status=Organization.STATUS.accepted,
                is_proposed=True,
            )
        elif FeatureFlag.flag_enabled("enable_results_display"):
            return self.get_winners()

        return Candidate.objects_with_org.none()

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


class CandidateResultsView(HubListView):
    allow_filters = ["domain"]
    paginate_by = 23
    template_name = "hub/candidate/results.html"

    def get_qs(self):
        if FeatureFlag.flag_enabled("enable_results_display"):
            return Candidate.objects_with_org.filter(
                org__status=Organization.STATUS.accepted, status=Candidate.STATUS.accepted, is_proposed=True
            )
        return Candidate.objects_with_org.none()

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
    template_name = "hub/candidate/detail.html"
    context_object_name = "candidate"
    model = Candidate

    def get_queryset(self):
        if (
            self.request.user
            and self.request.user.groups.filter(name__in=[COMMITTEE_GROUP, STAFF_GROUP, SUPPORT_GROUP]).exists()
        ):
            return Candidate.objects_with_org.select_related("org").prefetch_related("domain").all()

        return (
            Candidate.objects_with_org.select_related("org")
            .prefetch_related("domain")
            .filter(org__status=Organization.STATUS.accepted, is_proposed=True)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user: User = self.request.user
        candidate: Candidate = self.object

        context["can_support_candidate"] = False
        context["supported_candidate"] = False
        context["own_candidate"] = False
        context["can_approve_candidate"] = False
        context["approved_candidate"] = False
        context["can_vote_candidate"] = False
        context["voted_candidate"] = False
        context["used_all_domain_votes"] = False

        if user.is_anonymous:
            return context

        if candidate.org in user.orgs.all():
            context["own_candidate"] = True

        # Candidate Support checks
        if (
            FeatureFlag.flag_enabled(FLAG_CHOICES.global_support_round)
            and FeatureFlag.flag_enabled(FLAG_CHOICES.enable_candidate_supporting)
            and candidate.is_proposed
            and candidate.org.status == Organization.STATUS.accepted
            and user.orgs.first().status == Organization.STATUS.accepted
            and user.has_perm("hub.support_candidate")
        ):
            context["can_support_candidate"] = True
            if CandidateSupporter.objects.filter(user=user, candidate=candidate).exists():
                context["supported_candidate"] = True

        # Candidate: Approve checks
        if (
            FeatureFlag.flag_enabled(FLAG_CHOICES.enable_candidate_confirmation)
            and candidate.status == Candidate.STATUS.accepted
            and user.has_perm("hub.approve_candidate")
        ):
            context["can_approve_candidate"] = True
            if CandidateConfirmation.objects.filter(user=user, candidate=candidate).exists():
                context["approved_candidate"] = True

        # Candidate: Vote checks
        if (
            FeatureFlag.flag_enabled(FLAG_CHOICES.enable_candidate_voting)
            and candidate.status == Candidate.STATUS.confirmed
            and user.has_perm("hub.vote_candidate")
        ):
            context["can_vote_candidate"] = True
            if CandidateVote.objects.filter(user=user, candidate=candidate).exists():
                context["voted_candidate"] = True
            if CandidateVote.objects.filter(user=user, domain=candidate.domain).count() >= candidate.domain.seats:
                context["used_all_domain_votes"] = True

        return context


class CandidateRegisterRequestCreateView(LoginRequiredMixin, HubCreateView):
    template_name = "hub/candidate/register_request.html"
    model = Candidate
    form_class = CandidateRegisterForm

    def get(self, request, *args, **kwargs):
        if not FeatureFlag.flag_enabled("enable_candidate_registration"):
            raise PermissionDenied
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not FeatureFlag.flag_enabled("enable_candidate_registration"):
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
    template_name = "hub/candidate/update.html"
    model = Candidate
    form_class = CandidateUpdateForm

    def get_success_url(self):
        return reverse("candidate-update", args=(self.object.id,))

    def post(self, request, *args, **kwargs):
        if FeatureFlag.flag_enabled("enable_candidate_registration") or FeatureFlag.flag_enabled(
            "enable_candidate_supporting"
        ):
            return super().post(request, *args, **kwargs)
        raise PermissionDenied


@login_required
def candidate_vote(request, pk):
    if not FeatureFlag.flag_enabled(FLAG_CHOICES.enable_candidate_voting):
        raise PermissionDenied

    try:
        candidate = Candidate.objects.get(
            pk=pk, org__status=Organization.STATUS.accepted, status=Candidate.STATUS.confirmed, is_proposed=True
        )
        vote = CandidateVote.objects.create(user=request.user, candidate=candidate)
    except Exception:
        if settings.ENABLE_SENTRY:
            capture_message(f"User {request.user} tried to vote for candidate {pk} again.", level="warning")
        raise PermissionDenied

    if settings.VOTE_AUDIT_EMAIL:
        current_site = get_current_site(request)
        protocol = "https" if request.is_secure() else "http"
        send_email(
            subject=f"[VOTONG] Vot candidatură: {vote.candidate.name}",
            to_emails=[settings.VOTE_AUDIT_EMAIL],
            text_template="hub/emails/04_vote_audit.txt",
            html_template="hub/emails/04_vote_audit.html",
            context={
                "org": vote.user.orgs.first().name,
                "candidate": vote.candidate.name,
                "timestamp": timezone.localtime(vote.created).strftime("%H:%M:%S (%d/%m/%Y)"),
                "org_link": f"{protocol}://{current_site.domain}{vote.user.orgs.first().get_absolute_url()}",
                "candidate_link": f"{protocol}://{current_site.domain}{vote.candidate.get_absolute_url()}",
            },
        )

    return redirect("candidate-detail", pk=pk)


@login_required
@permission_required_or_403("hub.delete_candidate")
def candidate_revoke(request, pk):
    if not FeatureFlag.flag_enabled("enable_candidate_supporting"):
        raise PermissionDenied

    candidate = get_object_or_404(Candidate, pk=pk)

    if candidate.org != request.user.orgs.first():
        return redirect("candidate-detail", pk=pk)

    with transaction.atomic():
        candidate.supporters.all().delete()
        candidate.initial_org = candidate.org
        candidate.save()

    return redirect("candidate-register-request")


@login_required
@permission_required_or_403("hub.support_candidate")
def candidate_support(request, pk):
    if not FeatureFlag.flag_enabled("enable_candidate_supporting"):
        raise PermissionDenied

    user = request.user
    user_org = user.orgs.first()
    if user_org.status != Organization.STATUS.accepted:
        raise PermissionDenied

    candidate = get_object_or_404(Candidate, pk=pk, is_proposed=True)

    if candidate.org == user_org:
        return redirect("candidate-detail", pk=pk)

    try:
        supporter = CandidateSupporter.objects.get(user=request.user, candidate=candidate)
    except CandidateSupporter.DoesNotExist:
        CandidateSupporter.objects.create(user=request.user, candidate=candidate)
    else:
        supporter.delete()

    return redirect("candidate-detail", pk=pk)


@login_required
@permission_required_or_403("hub.approve_candidate")
def candidate_status_confirm(request, pk):
    if (
        FeatureFlag.flag_enabled("enable_candidate_registration")
        or FeatureFlag.flag_enabled("enable_candidate_supporting")
        or FeatureFlag.flag_enabled("enable_candidate_voting")
    ):
        raise PermissionDenied

    candidate: Candidate = get_object_or_404(Candidate, pk=pk)

    if candidate.org == request.user.orgs.first() or candidate.status == Candidate.STATUS.pending:
        return redirect("candidate-detail", pk=pk)

    confirmation, created = CandidateConfirmation.objects.get_or_create(user=request.user, candidate=candidate)

    if not created:
        message = f"User {request.user} tried to confirm candidate {candidate} status again."
        logger.warning(message)
        if settings.ENABLE_SENTRY:
            capture_message(message, level="warning")

    return redirect("candidate-detail", pk=pk)


@login_required
@permission_required_or_403("hub.change_organization")
def update_organization_information(request, pk):
    user = request.user
    user_is_admin = user.groups.filter(name__in=[STAFF_GROUP, SUPPORT_GROUP]).exists()
    user_is_org_owner = user.orgs.first().pk == pk
    if user.is_anonymous or (not user_is_admin and not user_is_org_owner):
        raise PermissionDenied

    return_url = request.GET.get("return_url", "")
    redirect_path = return_url or reverse("ngo-update", args=(pk,))

    minutes_threshold = 5
    update_threshold: datetime = timezone.now() - timezone.timedelta(minutes=minutes_threshold)

    organization: Organization = Organization.objects.get(pk=pk)
    organization_last_update: datetime = organization.ngohub_last_update_started
    if organization_last_update and organization_last_update > update_threshold:
        messages.error(
            request,
            _("Please wait %(minutes_threshold)s minutes before updating again.")
            % {"minutes_threshold": minutes_threshold},
        )
        return redirect(redirect_path)

    organization.ngohub_last_update_started = timezone.now()
    organization.save()

    update_organization(pk)

    return redirect(redirect_path)


class CityAutocomplete(View):
    def get(self, request):
        response = []
        county = request.GET.get("county")
        if county:
            cities = City.objects.filter(county__iexact=county).values_list("id", "city", named=True)
            response = [{"id": item.id, "city": item.city} for item in cities]
        return JsonResponse(response, safe=False)


class BlogListView(MenuMixin, ListView):
    model = BlogPost
    template_name = "hub/blog/list.html"
    paginate_by = 9

    def get_queryset(self):
        return BlogPost.objects.filter(is_visible=True, published_date__lte=timezone.now().date()).order_by(
            "-published_date"
        )


class BlogPostView(MenuMixin, DetailView):
    model = BlogPost
    template_name = "hub/blog/post.html"

    def get_queryset(self):
        return BlogPost.objects.filter(is_visible=True, published_date__lte=timezone.now().date())
