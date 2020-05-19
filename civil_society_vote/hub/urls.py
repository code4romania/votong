from django.urls import path, include

from hub.views import (
    OrganizationListView,
    OrganizationDetailView,
    OrganizationRegisterRequestCreateView,
)


urlpatterns = [
    path("", OrganizationListView.as_view(), name="ngos"),
    path("ngos/register", OrganizationRegisterRequestCreateView.as_view(), name="ngos-register-request",),
    path("ngos/<int:pk>", OrganizationDetailView.as_view(), name="ngo-detail"),
    path("i18n/", include("django.conf.urls.i18n")),
]
