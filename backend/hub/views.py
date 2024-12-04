import logging
import unicodedata
import hashlib
from datetime import datetime
from typing import Dict, List, Union
from urllib.parse import unquote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector, TrigramSimilarity
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q, QuerySet
from django.db.utils import IntegrityError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import CreateView, DetailView, FormView, ListView, UpdateView
from django.views.generic.base import ContextMixin
from guardian.decorators import permission_required_or_403
from guardian.mixins import LoginRequiredMixin, PermissionRequiredMixin
from sentry_sdk import capture_message

from accounts.models import (
    NGO_GROUP,
    NGO_USERS_GROUP,
    User,
)
from civil_society_vote.common.messaging import send_email
from hub.forms import (
    CandidateRegisterForm,
    CandidateUpdateForm,
    ContactForm,
    OrganizationCreateForm,
    OrganizationUpdateForm,
)
from hub.models import (
    FLAG_CHOICES,
    PHASE_CHOICES,
    SETTINGS_CHOICES,
    BlogPost,
    Candidate,
    CandidateConfirmation,
    CandidateSupporter,
    CandidateVote,
    City,
    Domain,
    FeatureFlag,
    Organization,
)
from hub.utils import decode_url_token_from_request, expiring_url
from hub.workers.update_organization import update_organization

logger = logging.getLogger(__name__)

UserModel = get_user_model()


def group_queryset_by_domain(
    queryset: QuerySet, *, domain_variable_name: str, sort_variable: str = "name"
) -> List[Dict[str, Union[Domain, List[Union[Organization, Candidate]]]]]:
    queryset_by_domain_dict: Dict[Domain, List[Union[Organization, Candidate]]] = {}

    all_domains = dict(Domain.objects.values_list("pk", "name"))

    domain_variable_name = f"{domain_variable_name}_id"

    for element in queryset:
        element_domain_pk: Domain = getattr(element, domain_variable_name)
        if element_domain_pk not in queryset_by_domain_dict:
            queryset_by_domain_dict[element_domain_pk] = []

        queryset_by_domain_dict[element_domain_pk].append(element)

    queryset_by_domain_list = []
    for domain_pk, query_item in queryset_by_domain_dict.items():
        domain_name = all_domains.get(domain_pk)
        snake_case_domain_key = "".join(filter(_filter_letter, domain_name)).lower().replace(" ", "_")
        normalized_domain_key = unicodedata.normalize("NFKD", snake_case_domain_key).encode("ascii", "ignore")

        queryset_by_domain_list.append(
            {
                "domain_pk": domain_pk,
                "domain_name": domain_name,
                "domain_key": normalized_domain_key.decode("utf-8"),
                "items": sorted(query_item, key=lambda x: getattr(x, sort_variable)),
            }
        )

    queryset_by_domain_list = sorted(queryset_by_domain_list, key=lambda x: x["domain_pk"])

    return queryset_by_domain_list


def _filter_letter(char: str) -> bool:
    if char.isalpha():
        return True
    elif char == " ":
        return True

    return False


class HealthView(View):
    # noinspection PyMethodMayBeStatic
    def get(self, request):
        base_response = {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "version": settings.VERSION,
            "revision": settings.REVISION,
        }

        user = request.user

        if user.is_anonymous:
            return JsonResponse(base_response)

        base_response["user"] = {
            "email": user.email,
        }

        if user.organization:
            base_response["user"]["organization"] = {
                "name": user.organization.name,
                "raf": user.organization.registration_number,
            }

        if not user.is_impersonate and not user.is_staff:
            return JsonResponse(base_response)

        if user.is_staff:
            base_response["user"].update(
                {
                    "is_staff": user.is_staff,
                    "is_superuser": user.is_superuser,
                    "is_impersonate": user.is_impersonate,
                }
            )

        if not user.is_impersonate:
            return JsonResponse(base_response)

        base_response["user"]["is_impersonate"] = user.is_impersonate

        base_response["impersonator"] = {
            "email": user.impersonator.email,
            "is_staff": user.impersonator.is_staff,
            "is_superuser": user.impersonator.is_superuser,
            "is_impersonate": user.impersonator.is_impersonate,
        }

        return JsonResponse(base_response)


class MenuMixin(ContextMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["contact_email"] = settings.CONTACT_EMAIL

        return context


class HomeView(MenuMixin, SuccessMessageMixin, FormView):
    template_name = "hub/home.html"
    form_class = ContactForm
    success_url = "/#contact"
    success_message = _("Thank you! We'll get in touch soon!")

    def form_valid(self, form):
        form.send_form_email()
        return super().form_valid(form)


class SearchMixin(MenuMixin, ListView):
    def search(self, queryset):
        # TODO: it should take into account selected language. Check only romanian for now.
        query = self.request.GET.get("q")
        if not query:
            return queryset

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

        return result


class HubDetailView(MenuMixin, DetailView):
    pass


class HubCreateView(MenuMixin, SuccessMessageMixin, CreateView):
    pass


class HubUpdateView(MenuMixin, SuccessMessageMixin, UpdateView):
    pass


class CommitteeOrganizationListView(LoginRequiredMixin, SearchMixin):
    allow_filters = ["status"]
    paginate_by = 9
    template_name = "hub/committee/list.html"

    def get_queryset(self):
        user = self.request.user
        if not user or user.is_anonymous or not user.in_committee_or_staff_groups():
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
        "candidates_pending": Candidate.proposed.filter(status=Candidate.STATUS.pending).count(),
        "candidates_accepted": Candidate.proposed.filter(status=Candidate.STATUS.accepted).count(),
        "candidates_confirmed": Candidate.proposed.filter(status=Candidate.STATUS.confirmed).count(),
        "candidates_rejected": Candidate.proposed.filter(status=Candidate.STATUS.rejected).count(),
    }


class CommitteeCandidatesListView(LoginRequiredMixin, SearchMixin):
    allow_filters = ["status"]
    paginate_by = 9
    template_name = "hub/committee/candidates.html"

    def get_queryset(self):
        user = self.request.user
        if not user or user.is_anonymous or not user.in_committee_or_staff_groups():
            raise PermissionDenied

        filters = {name: self.request.GET[name] for name in self.allow_filters if self.request.GET.get(name)}
        return (
            Candidate.proposed.filter(**filters)
            .annotate(supporters_count=Count("supporters"))
            .order_by("domain__name", "-supporters_count")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filtering"] = self.request.GET.get("status", Candidate.STATUS.pending)
        context["counters"] = _get_candidates_counters()
        return context


class ElectorCandidatesListView(LoginRequiredMixin, SearchMixin):
    allow_filters = ["status"]
    paginate_by = 9
    template_name = "hub/ngo/votes.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        domains = []

        if FeatureFlag.flag_enabled(SETTINGS_CHOICES.enable_voting_domain):
            user_org = self.request.user.organization
            if user_org and user_org.voting_domain:
                domains = [user_org.voting_domain]
        else:
            domains = Domain.objects.order_by("id").all()

        context["domains"] = domains

        return context

    def get_queryset(self):
        if not self.request.user.groups.filter(name__in=[NGO_GROUP, NGO_USERS_GROUP]).exists():
            raise PermissionDenied

        voted_candidates = CandidateVote.objects.filter(organization__pk=self.request.user.organization_id)
        return [element.candidate for element in voted_candidates]


class OrganizationListView(SearchMixin):
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
        queryset = self.search(self.get_qs())
        filters = {name: self.request.GET[name] for name in self.allow_filters if self.request.GET.get(name)}
        queryset_filtered = queryset.filter(**filters)

        if FeatureFlag.flag_enabled(SETTINGS_CHOICES.enable_voting_domain):
            return group_queryset_by_domain(queryset_filtered, domain_variable_name="voting_domain")

        return queryset_filtered

    def get_cached_context(self, context_cache_key, orgs) -> Dict:
        sentinel = object()
        context_cache = cache.get(context_cache_key, sentinel)
        if context_cache is not sentinel:
            return context_cache

        context_cache = {}

        context_cache["counties"] = list(orgs.order_by("county").values_list("county", flat=True).distinct("county"))
        if self.request.GET.get("county"):
            orgs = orgs.filter(county=self.request.GET.get("county"))

        context_cache["cities"] = set(orgs.values_list("city__id", "city__city"))

        context_cache["counters"] = {
            "ngos_accepted": int(Organization.objects.filter(status=Organization.STATUS.accepted).count())
        }

        if self.request.GET.get("city"):
            try:
                context_cache["current_city_name"] = City.objects.get(id=self.request.GET.get("city")).city
            except City.DoesNotExist:
                context_cache["current_city_name"] = "-"

        cache.set(context_cache_key, context_cache, settings.TIMEOUT_CACHE_SHORT)

        return context_cache

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        orgs: QuerySet[Organization] = self.search(self.get_qs())

        context["current_search"] = self.request.GET.get("q", "").strip()[:100]
        context["current_county"] = self.request.GET.get("county")
        context["current_city"] = self.request.GET.get("city")

        # noinspection InsecureHash
        param_hash = hashlib.sha256(
            f"{context['current_county'] or ''}_{context['current_city'] or ''}_{context['current_search']}".encode()
        ).hexdigest()

        context["listing_cache_duration"] = settings.TIMEOUT_CACHE_SHORT
        context["listing_cache_key"] = f"orgs_listing_{param_hash}"
        context_cache_key = f"orgs_listing_context_{param_hash}"

        context_cache = self.get_cached_context(context_cache_key, orgs)
        context.update(context_cache)

        return context


class OrganizationDetailView(HubDetailView):
    template_name = "hub/ngo/detail.html"
    context_object_name = "ngo"
    model = Organization

    def get_queryset(self):
        user: User = self.request.user

        if org_pk := self.kwargs.get("pk"):
            if user.is_authenticated and user.organization and user.organization.pk == org_pk:
                return Organization.objects.filter(pk=org_pk)
            return Organization.objects.filter(pk=org_pk, status=Organization.STATUS.accepted)

        return Organization.objects.filter(status=Organization.STATUS.accepted)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user: UserModel = self.request.user
        organization: Organization = self.object

        context["can_view_all_information"] = False
        context["should_display_organization_documents"] = False

        if user.is_anonymous:
            return context

        if user.in_committee_or_staff_groups():
            context["can_view_all_information"] = True

        if (
            organization.report_2023
            or organization.report_2022
            or organization.report_2021
            or organization.statement_discrimination
            or (
                context["can_view_all_information"]
                and (
                    organization.last_balance_sheet
                    or organization.statute
                    or organization.fiscal_certificate_anaf
                    or organization.fiscal_certificate_local
                    or organization.statement_political
                )
            )
        ):
            context["should_display_organization_documents"] = True

        return context


class OrganizationRegisterRequestCreateView(HubCreateView):
    template_name = "hub/ngo/register_request.html"
    model = Organization
    form_class = OrganizationCreateForm
    success_message = (
        _(
            "Thank you for signing up! The form you filled in has reached us. Someone from our team will reach out to you "
            "as soon as your organization is validated. If you have any further questions, send us a message at %s."
        )
        % settings.CONTACT_EMAIL
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        return context

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

        update_button_class = "is-warning"
        update_button_message = _("Update organization's profile")
        update_button_description = _("Some data in this organization's profile can only be updated through NGO Hub.")
        if organization.status == Organization.STATUS.accepted:
            update_button_class = "is-success"
            update_button_message = _("The organization's information is complete")
            update_button_description = _(
                "If you have recently edited information in the organization's account on NGO Hub and want to update it in the profile on VotONG, click here"
            )

        context.update(
            {
                "update_button_class": update_button_class,
                "update_button_message": update_button_message,
                "update_button_description": update_button_description,
            }
        )

        if FeatureFlag.flag_enabled(SETTINGS_CHOICES.enable_voting_domain) and not organization.voting_domain:
            context["voting_domain_warning"] = _(
                "The organization does not have the voting domain set. "
                "To be able to vote, please set the voting domain."
            )

        return context

    def get_success_url(self):
        return reverse("ngo-update", args=(self.object.id,))

    def post(self, request, *args, **kwargs):
        if FeatureFlag.flag_enabled(FLAG_CHOICES.enable_org_editing) or FeatureFlag.flag_enabled(
            FLAG_CHOICES.enable_candidate_editing
        ):
            return super().post(request, *args, **kwargs)

        ngo_id = self.kwargs.get("pk")
        if not ngo_id:
            return redirect("home")

        return redirect(reverse("ngo-update", args=(ngo_id,)))


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


class CandidateListView(SearchMixin):
    allow_filters = ["domain"]
    paginate_by = 200
    template_name = "hub/candidate/list.html"

    @classmethod
    def get_candidates_to_vote(cls):
        return (
            Candidate.objects_with_org.filter(
                org__status=Organization.STATUS.accepted,
                status=Candidate.STATUS.confirmed,
                is_proposed=True,
            )
            .select_related("org")
            .prefetch_related("domain")
        )

    @classmethod
    def get_candidates_pending(cls):
        return (
            Candidate.objects_with_org.filter(
                org__status=Organization.STATUS.accepted,
                is_proposed=True,
            )
            .select_related("org")
            .prefetch_related("domain")
        )

    def get_qs(self):
        if FeatureFlag.flag_enabled(PHASE_CHOICES.enable_candidate_voting) or FeatureFlag.flag_enabled(
            PHASE_CHOICES.enable_pending_results
        ):
            return self.get_candidates_to_vote()

        if FeatureFlag.flag_enabled(PHASE_CHOICES.enable_results_display):
            return Candidate.objects_with_org.none()

        return self.get_candidates_pending()

    def get_queryset(self):
        qs = self.search(self.get_qs())

        filters = {name: self.request.GET[name] for name in self.allow_filters if self.request.GET.get(name)}

        queryset_filtered = qs.filter(**filters)

        if not FeatureFlag.flag_enabled(SETTINGS_CHOICES.single_domain_round):
            return group_queryset_by_domain(queryset_filtered, domain_variable_name="domain")

        return queryset_filtered

    def _get_candidate_counters(self):
        candidates = self.get_qs()
        return {
            "candidates_pending": candidates.filter(is_proposed=True).count(),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_search"] = self.request.GET.get("q", "")

        context["should_display_candidates"] = False
        if not FeatureFlag.flag_enabled(PHASE_CHOICES.enable_results_display):
            context["should_display_candidates"] = True

        current_domain = self.request.GET.get("domain")
        if current_domain:
            try:
                context["current_domain"] = Domain.objects.get(id=current_domain)
            except Domain.DoesNotExist:
                pass

        context["counters"] = self._get_candidate_counters()
        context["domains"] = Domain.objects.all()
        context["listing_cache_duration"] = settings.TIMEOUT_CACHE_SHORT
        # noinspection InsecureHash
        context["listing_cache_key"] = hashlib.sha256(
            f"candidates_listing_{current_domain if current_domain else ''}_{context['current_search']}".encode()
        ).hexdigest()

        return context


class AllCandidatesListView(CandidateListView):
    template_name = "hub/candidate/all.html"

    def get_queryset(self):
        qs = self.search(self.get_candidates_pending())

        filters = {name: self.request.GET[name] for name in self.allow_filters if self.request.GET.get(name)}

        queryset_filtered = qs.filter(**filters)

        queryset_filtered = queryset_filtered.order_by("status", "domain__id", "name")

        return queryset_filtered


class CandidateResultsView(SearchMixin):
    allow_filters = ["domain"]
    paginate_by = 100
    template_name = "hub/candidate/results.html"

    def get_qs(self):
        if FeatureFlag.flag_enabled("enable_results_display") or (
            self.request.user and self.request.user.in_staff_groups()
        ):
            return Candidate.objects_with_org.filter(
                org__status=Organization.STATUS.accepted,
                status=Candidate.STATUS.confirmed,
                is_proposed=True,
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
        user = self.request.user
        candidat_base_queryset = Candidate.objects_with_org.select_related("org").prefetch_related("domain")

        if user and not user.is_anonymous and user.in_committee_or_staff_groups():
            return candidat_base_queryset.all()

        return candidat_base_queryset.filter(org__status=Organization.STATUS.accepted, is_proposed=True)

    def _get_candidate_support_context(self, user: User, candidate: Candidate) -> Dict[str, bool]:
        context = {
            "can_support_candidate": False,
            "supported_candidate": False,
        }

        if not FeatureFlag.flag_enabled(SETTINGS_CHOICES.global_support_round):
            return context

        if not FeatureFlag.flag_enabled(PHASE_CHOICES.enable_candidate_supporting):
            return context

        if not candidate.is_proposed:
            return context

        if not candidate.org.status == Organization.STATUS.accepted:
            return context

        if not user.has_perm("hub.support_candidate"):
            return context

        organization = user.organization

        if not organization:
            return context

        # An organization can support candidates from any domain
        if not organization.is_elector(organization.voting_domain):
            return context

        context["can_support_candidate"] = True

        if CandidateSupporter.objects.filter(user__pk__in=user.org_user_pks(), candidate=candidate).exists():
            context["supported_candidate"] = True

        return context

    def _get_candidate_approval_context(self, user: User, candidate: Candidate) -> Dict[str, bool]:
        context = {
            "can_see_approval_action": False,
            "can_approve_candidate": False,
            "approved_candidate": False,
        }

        if not FeatureFlag.flag_enabled(PHASE_CHOICES.enable_candidate_confirmation):
            return context

        if not candidate.status == Candidate.STATUS.accepted:
            return context

        if not user.in_commission_groups():
            return context

        context["can_see_approval_action"] = True

        if not user.has_perm("hub.approve_candidate"):
            return context

        context["can_approve_candidate"] = True

        if CandidateConfirmation.objects.filter(user=user, candidate=candidate).exists():
            context["approved_candidate"] = True

        return context

    def _get_candidate_vote_context(self, user: User, candidate: Candidate) -> Dict[str, bool]:
        context = {
            "user_has_organization": False,
            "organization_has_domain": False,
            "can_vote_candidate": False,
            "voted_candidate": False,
            "used_all_domain_votes": False,
        }

        if not FeatureFlag.flag_enabled(PHASE_CHOICES.enable_candidate_voting):
            return context

        if not candidate.status == Candidate.STATUS.confirmed:
            return context

        if not user.has_perm("hub.vote_candidate"):
            return context

        domain = candidate.domain

        # An organization can only vote for candidates from its own domain
        user_org = user.organization
        if not user_org:
            return context

        context["user_has_organization"] = True

        if not user_org.voting_domain:
            return context

        context["organization_has_domain"] = True

        if not user_org.is_elector(domain):
            return context

        context["can_vote_candidate"] = True

        if CandidateVote.objects.filter(organization=user_org, candidate=candidate).exists():
            context["voted_candidate"] = True

        if CandidateVote.objects.filter(organization=user_org, domain=domain).count() >= domain.seats:
            context["used_all_domain_votes"] = True

        return context

    def _build_candidate_status_explainer(self) -> Dict:
        """
        Build a dictionary with the candidate statuses and their explanations.
        The dictionary has the following format:
        {
            <status>: {
                "title": <The verbose title string of the status>,
                "detail": <The description of what that status means>,
                "period": [Optional] <The period of time the candidate is in that status>,
            }
        }
        """

        candidate_statuses = {
            Candidate.STATUS.pending: {
                "title": Candidate.STATUS[Candidate.STATUS.pending],
                "detail": _("The candidate has been proposed and is gathering the necessary support."),
            },
            Candidate.STATUS.accepted: {
                "title": Candidate.STATUS[Candidate.STATUS.accepted],
                "detail": _("The candidate has been approved by the admins and is waiting for validation."),
            },
            Candidate.STATUS.confirmed: {
                "title": Candidate.STATUS[Candidate.STATUS.confirmed],
                "detail": _("The candidate has been validated by the electoral commission and can be voted."),
            },
            Candidate.STATUS.rejected: {
                "title": Candidate.STATUS[Candidate.STATUS.rejected],
                "detail": _("The candidate has been rejected by the admins or the electoral commission."),
            },
        }

        status_explainers = {}

        for status, status_data in candidate_statuses.items():
            status_explainer = f"{status_data['title']}: {status_data['detail']}"
            if "period" in status_data:
                status_explainer += f"\n{status_data['period']}"
            status_explainers[status] = status_explainer

        return status_explainers

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "own_candidate": False,
                "can_support_candidate": False,
                "supported_candidate": False,
                "can_approve_candidate": False,
                "approved_candidate": False,
                "can_vote_candidate": False,
                "voted_candidate": False,
                "used_all_domain_votes": False,
                "can_view_all_information": False,
            }
        )

        user: User = self.request.user
        candidate: Candidate = self.object

        candidate_status = candidate.STATUS[candidate.status]
        context["candidate_status"] = candidate_status
        context["display_candidate_validation_label"] = False
        context["candidate_status_explainer"] = self._build_candidate_status_explainer()[candidate.status]

        if user.is_anonymous:
            return context

        if candidate.org == user.organization:
            context["own_candidate"] = True

        # Candidate Support checks
        context.update(self._get_candidate_support_context(user, candidate))

        # Candidate: Approve checks
        context.update(self._get_candidate_approval_context(user, candidate))

        # Candidate: Vote checks
        context.update(self._get_candidate_vote_context(user, candidate))

        if user.in_committee_or_staff_groups():
            context["can_view_all_information"] = True

        if user.in_commission_groups() and candidate.status != Candidate.STATUS.pending:
            context["display_candidate_validation_label"] = True

        return context


class CandidateRegisterRequestCreateView(LoginRequiredMixin, HubCreateView):
    template_name = "hub/candidate/register_request.html"
    model = Candidate
    form_class = CandidateRegisterForm

    def _check_permissions(self, request):
        if not FeatureFlag.flag_enabled(PHASE_CHOICES.enable_candidate_registration):
            raise PermissionDenied

        if not request.user or request.user.is_anonymous:
            raise PermissionDenied(_("User is not authenticated."))

        user_org = request.user.organization

        if not user_org:
            raise PermissionDenied(_("Authenticated user does not have an organization."))

        if Candidate.objects_with_org.filter(org=user_org).exists():
            return redirect(reverse("candidate-update", args=(user_org.candidate.pk,)))

    def get(self, request, *args, **kwargs):
        check_result = self._check_permissions(request)
        if check_result:
            return check_result

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        check_result = self._check_permissions(request)
        if check_result:
            return check_result

        try:
            return super().post(request, *args, **kwargs)
        except IntegrityError as exc:
            if "hub_candidate_org_id_key" in str(exc):
                existing_candidate_pk = request.user.organization.candidate.pk
                logger.info(
                    f"User {request.user} tried to create a new candidate when one already exists. "
                    f"Redirecting to existing candidate {existing_candidate_pk}."
                )

                return redirect(reverse("candidate-update", args=(existing_candidate_pk,)))

            raise exc

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        can_propose_candidate = False

        user = self.request.user
        user_org: Organization = user.organization
        candidate: Candidate = self.object

        if (
            FeatureFlag.flag_enabled(PHASE_CHOICES.enable_candidate_registration)
            and user_org
            and user_org.is_complete_for_candidate
            and candidate
            and candidate.is_complete
        ):
            can_propose_candidate = True

        context["can_propose_candidate"] = can_propose_candidate

        organization_missing_fields = []
        candidate_missing_fields = []

        if not can_propose_candidate:
            if user_org and not user_org.is_complete_for_candidate:
                organization_missing_fields = user_org.get_missing_fields_for_candidate()
                organization_missing_fields = [f"'{str(field.verbose_name)}'" for field in organization_missing_fields]

            if candidate and not candidate.is_complete:
                candidate_missing_fields = candidate.get_missing_fields()
                candidate_missing_fields = [f"'{str(field.verbose_name)}'" for field in candidate_missing_fields]

        if organization_missing_fields or candidate_missing_fields:
            context["organization_missing_fields"] = ", ".join(organization_missing_fields)
            context["candidate_missing_fields"] = ", ".join(candidate_missing_fields)

        return context

    def get_form_kwargs(self):
        kwargs = super(CandidateUpdateView, self).get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("candidate-update", args=(self.object.id,))

    def post(self, request, *args, **kwargs):
        if not FeatureFlag.flag_enabled(PHASE_CHOICES.enable_candidate_editing):
            raise PermissionDenied(_("Candidate editing disabled"))

        user = self.request.user
        user_org: Organization = user.organization
        candidate: Candidate = self.get_object()

        if not user_org:
            raise PermissionDenied(_("No user organization"))

        if not candidate:
            raise PermissionDenied(_("No candidate"))

        if not candidate == user_org.candidate:
            raise PermissionDenied(_("Candidate does not belong to user organization"))

        return super().post(request, *args, **kwargs)


@login_required
def candidate_vote(request, pk):
    if not FeatureFlag.flag_enabled(PHASE_CHOICES.enable_candidate_voting):
        raise PermissionDenied

    candidate = get_object_or_404(Candidate, pk=pk, is_proposed=True, status=Candidate.STATUS.confirmed)

    user: User = request.user
    user_org = user.organization
    if user_org.status != Organization.STATUS.accepted:
        raise PermissionDenied

    if CandidateVote.objects.filter(organization_id=user_org.id, candidate=candidate).exists():
        raise PermissionDenied(_("A candidate can't be voted twice by the same organization."))

    try:
        vote = CandidateVote.objects.create(user=request.user, organization=user_org, candidate=candidate)
    except Exception:
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
                "org": vote.user.organization.name,
                "candidate": vote.candidate.name,
                "timestamp": timezone.localtime(vote.created).strftime("%H:%M:%S (%d/%m/%Y)"),
                "org_link": f"{protocol}://{current_site.domain}{vote.user.organization.get_absolute_url()}",
                "candidate_link": f"{protocol}://{current_site.domain}{vote.candidate.get_absolute_url()}",
            },
        )

    return redirect("candidate-detail", pk=pk)


@login_required
def candidate_revoke(request, pk):
    if not FeatureFlag.flag_enabled("enable_candidate_supporting"):
        raise PermissionDenied

    candidate = get_object_or_404(Candidate, pk=pk)

    if candidate.org != request.user.organization:
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

    candidate = get_object_or_404(Candidate, pk=pk, is_proposed=True)

    user: User = request.user
    user_org = user.organization
    if user_org.status != Organization.STATUS.accepted:
        raise PermissionDenied

    if candidate.org == user_org:
        return redirect("candidate-detail", pk=pk)

    supporter = CandidateSupporter.objects.filter(user__pk__in=request.user.org_user_pks(), candidate=candidate)
    if supporter.exists():
        supporter.delete()
    else:
        CandidateSupporter.objects.create(user=request.user, candidate=candidate)

    return redirect("candidate-detail", pk=pk)


@login_required
@permission_required_or_403("hub.approve_candidate")
def candidate_status_confirm(request, pk):
    if (
        FeatureFlag.flag_enabled(PHASE_CHOICES.enable_candidate_registration)
        or FeatureFlag.flag_enabled(PHASE_CHOICES.enable_candidate_editing)
        or FeatureFlag.flag_enabled(PHASE_CHOICES.enable_candidate_supporting)
        or FeatureFlag.flag_enabled(PHASE_CHOICES.enable_candidate_voting)
    ):
        raise PermissionDenied

    candidate: Candidate = get_object_or_404(Candidate, pk=pk)

    if candidate.org == request.user.organization or candidate.status == Candidate.STATUS.pending:
        return redirect("candidate-detail", pk=pk)

    confirmation, created = CandidateConfirmation.objects.get_or_create(user=request.user, candidate=candidate)

    if not created:
        message = f"User {request.user} tried to confirm candidate {candidate} status again."
        logger.warning(message)
        if settings.ENABLE_SENTRY:
            capture_message(message, level="warning")

    return redirect("candidate-detail", pk=pk)


@login_required
@expiring_url()
@permission_required_or_403("hub.approve_candidate")
def reset_candidate_confirmations(
    request,
):
    if request.method != "POST":
        return render(request, "hub/committee/delete_confirmations.html")

    decoded_token = decode_url_token_from_request(request=request)
    if not decoded_token:
        raise Http404

    user_request_pk = int(decoded_token.get("subject_pk", None))
    if request.user.pk != user_request_pk:
        raise PermissionDenied(_("Cannot delete another user's confirmations"))

    for confirmation in CandidateConfirmation.objects.filter(user=request.user):
        confirmation.delete()

    messages.success(request, _("Confirmations successfully deleted"))

    return redirect(reverse("candidates"))


@login_required
@permission_required_or_403("hub.change_organization")
def update_organization_information(request, pk):
    user: User = request.user
    user_is_admin = user.in_staff_groups()
    user_is_org_owner = user.organization.pk == pk
    if user.is_anonymous or (not user_is_admin and not user_is_org_owner):
        raise PermissionDenied

    return_url = request.GET.get("return_url", "")
    redirect_path = return_url or reverse("ngo-update", args=(pk,))

    minutes_threshold = 5
    update_threshold: datetime = timezone.now() - timezone.timedelta(minutes=minutes_threshold)

    organization: Organization = Organization.objects.get(pk=pk)
    organization_last_update: datetime = organization.ngohub_last_update_started
    if not settings.DEBUG and organization_last_update and organization_last_update > update_threshold:
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
