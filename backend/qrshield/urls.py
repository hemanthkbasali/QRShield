from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("scanner.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler400 = "scanner.views.bad_request"
handler403 = "scanner.views.permission_denied"
handler404 = "scanner.views.page_not_found"
handler500 = "scanner.views.server_error"
