from django.urls import include, path
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.cache import cache_page

from hub.views import (
    CandidateDetailView,
    CandidateListView,
    CandidateRegisterRequestCreateView,
    CandidateResultsView,
    CandidateUpdateView,
    CityAutocomplete,
    CommitteeCandidatesListView,
    CommitteeOrganizationListView,
    ElectorCandidatesListView,
    HomeView,
    OrganizationDetailView,
    OrganizationListView,
    OrganizationRegisterRequestCreateView,
    OrganizationUpdateView,
    candidate_revoke,
    candidate_status_confirm,
    candidate_support,
    candidate_vote,
    organization_vote,
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path(_("candidates/"), CandidateListView.as_view(), name="candidates"),
    path(_("candidates/register"), CandidateRegisterRequestCreateView.as_view(), name="candidate-register-request",),
    path(_("candidates/<int:pk>"), CandidateDetailView.as_view(), name="candidate-detail"),
    path(_("candidates/<int:pk>/vote"), candidate_vote, name="candidate-vote"),
    path(_("candidates/<int:pk>/support"), candidate_support, name="candidate-support"),
    path(_("candidates/<int:pk>/revoke"), candidate_revoke, name="candidate-revoke"),
    path(_("candidates/<int:pk>/status-confirm"), candidate_status_confirm, name="candidate-status-confirm"),
    path(_("candidates/<int:pk>/update"), CandidateUpdateView.as_view(), name="candidate-update"),
    path(_("candidates/votes"), ElectorCandidatesListView.as_view(), name="votes"),
    path(_("candidates/ces-results"), CandidateResultsView.as_view(), name="ces-results"),
    path(_("committee/ngos/"), CommitteeOrganizationListView.as_view(), name="committee-ngos"),
    path(_("committee/candidates/"), CommitteeCandidatesListView.as_view(), name="committee-candidates"),
    path(_("ngos/"), OrganizationListView.as_view(), name="ngos"),
    path(_("ngos/register"), OrganizationRegisterRequestCreateView.as_view(), name="ngos-register-request",),
    path(_("ngos/<int:pk>"), OrganizationDetailView.as_view(), name="ngo-detail"),
    path(_("ngos/<int:pk>/vote/<str:action>"), organization_vote, name="ngo-vote"),
    path(_("ngos/<int:pk>/update"), OrganizationUpdateView.as_view(), name="ngo-update"),
    path("ngos/city-autocomplete/", CityAutocomplete.as_view(), name="city-autocomplete"),
    path("i18n/", include("django.conf.urls.i18n")),
]
