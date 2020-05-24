from django.urls import path, include

from hub.views import (
    OrganizationListView,
    OrganizationDetailView,
    OrganizationRegisterRequestCreateView,
    CityAutocomplete,
    CandidateListView,
    CandidateRegisterRequestCreateView,
    CandidateDetailView,
)


urlpatterns = [
    path("", CandidateListView.as_view(), name="candidates"),
    path("candidate/register", CandidateRegisterRequestCreateView.as_view(), name="candidate-register-request",),
    path("candidate/<int:pk>", CandidateDetailView.as_view(), name="candidate-detail"),
    path("ngos/", OrganizationListView.as_view(), name="ngos"),
    path("ngos/register", OrganizationRegisterRequestCreateView.as_view(), name="ngos-register-request",),
    path("ngos/<int:pk>", OrganizationDetailView.as_view(), name="ngo-detail"),
    path("ngos/city-autocomplete/", CityAutocomplete.as_view(), name="city-autocomplete"),
    path("i18n/", include("django.conf.urls.i18n")),
]
