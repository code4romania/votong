from django.urls import path, include

from hub.views import (
    NGOListView,
    NGODetailView,
    NGORegisterRequestCreateView,
)


urlpatterns = [
    path("", NGOListView.as_view(), name="ngos"),
    path(
        "ngos/register",
        NGORegisterRequestCreateView.as_view(),
        name="ngos-register-request",
    ),
    path("ngos/<int:pk>", NGODetailView.as_view(), name="ngo-detail"),
    path("i18n/", include("django.conf.urls.i18n")),
]
