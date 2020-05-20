from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib.auth import views as auth_views
from django.utils.translation import ugettext_lazy as _

from civil_society_vote.views import StaticPageView


admin.site.site_title = _("Admin Civil Society Vote")
admin.site.site_header = _("Admin Civil Society Vote")
admin.site.index_title = _("Admin Civil Society Vote")


urlpatterns = i18n_patterns(
    path("about/", StaticPageView.as_view(template_name="about.html"), name="about"),
    path("rules/", StaticPageView.as_view(template_name="rules.html"), name="rules"),
    path("contact/", StaticPageView.as_view(template_name="contact.html"), name="contact"),
    path("terms/", StaticPageView.as_view(template_name="terms_and_conditions.html"), name="terms",),
    path("cookies/", StaticPageView.as_view(template_name="cookies.html"), name="cookies"),
    path("updates/", StaticPageView.as_view(template_name="updates.html"), name="updates"),
    path("admin/", admin.site.urls),
    path(
        "admin/password_reset/",
        auth_views.PasswordResetView.as_view(html_email_template_name="registration/password_reset_email.html"),
        name="admin_password_reset",
    ),
    path("admin/password_reset/done/", auth_views.PasswordResetDoneView.as_view(), name="password_reset_done",),
    path(
        "admin/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(template_name="registration/set_password.html"),
        name="password_reset_confirm",
    ),
    path("admin/reset/done/", auth_views.PasswordResetCompleteView.as_view(), name="password_reset_complete",),
    path("", include("hub.urls")),
)

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
