from django.urls import include, path

from hub.views import (
    CandidateDetailView,
    CandidateListView,
    CandidateRegisterRequestCreateView,
    CandidateVoteView,
    CityAutocomplete,
    HomeView,
    OrganizationDetailView,
    OrganizationListView,
    OrganizationRegisterRequestCreateView,
    OrganizationVoteView,
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("candidates/", CandidateListView.as_view(), name="candidates"),
    path("candidate/register", CandidateRegisterRequestCreateView.as_view(), name="candidate-register-request",),
    path("candidate/<int:pk>", CandidateDetailView.as_view(), name="candidate-detail"),
    path("candidate/<int:pk>/vote", CandidateVoteView.as_view(), name="candidate-vote"),
    path("ngos/", OrganizationListView.as_view(), name="ngos"),
    path("ngos/register", OrganizationRegisterRequestCreateView.as_view(), name="ngos-register-request",),
    path("ngos/<int:pk>", OrganizationDetailView.as_view(), name="ngo-detail"),
    path("ngos/<int:pk>/vote", OrganizationVoteView.as_view(), name="ngo-vote"),
    path("ngos/city-autocomplete/", CityAutocomplete.as_view(), name="city-autocomplete"),
    path("i18n/", include("django.conf.urls.i18n")),
]
