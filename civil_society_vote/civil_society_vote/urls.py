from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path
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
    path("impersonate/", include("impersonate.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("hub.urls")),
)

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
