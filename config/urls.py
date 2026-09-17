from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from core.views import public_media

urlpatterns = [
    path("media/public/<path:path>", public_media, name="public_media"),
    path("secure-admin/", admin.site.urls),
    path("", include("core.urls")),
    path("account/", include("accounts.urls")),
    path("schools/", include("schools.urls")),
    path("news/", include("content.urls")),
    path("information/", include("content.page_urls")),
    path("downloads/", include("content.download_urls")),
    path("issuances/", include("issuances.urls")),
    path("services/", include("services.urls")),
    path("appointments/", include("appointments.urls")),
    path("helpdesk/", include("tickets.urls")),
    path("feedback/", include("feedback.urls")),
    path("vacancies/", include("vacancies.urls")),
    path("events/", include("events.urls")),
    path("verify/", include("verification.urls")),
    path("notifications/", include("notifications.urls")),
]
handler400="core.views.error_400"
handler403="core.views.error_403"
handler404="core.views.error_404"
handler500="core.views.error_500"
if settings.DEBUG: urlpatterns+=static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
