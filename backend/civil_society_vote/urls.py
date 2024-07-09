from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import RedirectView

from civil_society_vote.views import StaticPageView

admin.site.site_title = _("Admin Civil Society Vote")
admin.site.site_header = _("Admin Civil Society Vote")
admin.site.index_title = _("Admin Civil Society Vote")


urlpatterns = i18n_patterns(
    path(_("about/"), StaticPageView.as_view(template_name="about.html"), name="about"),
    path(_("rules/"), StaticPageView.as_view(template_name="rules.html"), name="rules"),
    path(
        _("terms/"),
        StaticPageView.as_view(template_name="terms_and_conditions.html"),
        name="terms",
    ),
    path(
        _("comittee_public_statement/"),
        StaticPageView.as_view(template_name="comittee_statement.html"),
        name="comittee_public_statement",
    ),
    path("cookies/", StaticPageView.as_view(template_name="cookies.html"), name="cookies"),
    path(_("platform_rules/"), StaticPageView.as_view(template_name="platform_rules.html"), name="platform_rules"),
    path(_("history/"), StaticPageView.as_view(template_name="history.html"), name="history"),
    path("admin/", admin.site.urls),
    path("impersonate/", include("impersonate.urls")),
    path("ckeditor/", include("ckeditor_uploader.urls")),
    path(
        _("accounts/error/registration-closed/"),
        StaticPageView.as_view(template_name="error_org_registration_closed.html"),
        name="error-org-registration-closed",
    ),
    path(
        _("accounts/error/duplicate-organization/"),
        StaticPageView.as_view(template_name="error_org_duplicate.html"),
        name="error-org-duplicate",
    ),
    path(
        _("accounts/error/missing-organization/"),
        StaticPageView.as_view(template_name="error_org_missing.html"),
        name="error-org-missing",
    ),
    path(_("accounts/"), include("django.contrib.auth.urls")),
    path(
        _("accounts/reset-password/"),
        auth_views.PasswordResetView.as_view(
            html_email_template_name="registration/reset_password_email.html",
            template_name="registration/reset_password.html",
        ),
        name="password_reset",
    ),
    path(
        _("accounts/reset-password/done/"),
        auth_views.PasswordResetDoneView.as_view(template_name="registration/reset_password_done.html"),
        name="password_reset_done",
    ),
    path(
        _("accounts/reset-password/<uidb64>/<token>/"),
        auth_views.PasswordResetConfirmView.as_view(template_name="registration/reset_password_confirm.html"),
        name="password_reset_confirm",
    ),
    path(
        _("accounts/reset-password/complete/"),
        auth_views.PasswordResetCompleteView.as_view(template_name="registration/reset_password_complete.html"),
        name="password_reset_complete",
    ),
    path("me/", include("accounts.urls")),
    path(
        "allauth/login/", RedirectView.as_view(url="/allauth/amazon-cognito/login/", permanent=True)
    ),  # Skip the provider selector page and redirect to Cognito
    path("allauth/", include("allauth.urls")),
    path("", include("hub.urls")),
)

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
