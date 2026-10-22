"""URL utama SIGAP JUMBARA."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView

admin.site.site_header = "SIGAP JUMBARA (darurat)"
admin.site.site_title = "SIGAP JUMBARA"
admin.site.index_title = "Admin darurat. Gunakan menu superadmin untuk pekerjaan sehari-hari."

urlpatterns = [
    path("", include("apps.biodata.urls")),
    path("", include("apps.akun.urls")),
    path("api/", include("apps.absensi.urls_api")),
    path("superadmin/kartu/", include("apps.kartu.urls")),
    path("superadmin/", include("apps.biodata.urls_admin")),
    path("superadmin/kontingen/", include("apps.kontingen.urls")),
    path("superadmin/akun/", include("apps.akun.urls_admin")),
    path("superadmin/", include("apps.inti.urls_admin")),
    # Login admin bawaan dialihkan ke halaman masuk SIGAP (punya batas percobaan).
    path("django-admin/login/", RedirectView.as_view(url="/masuk/?next=/django-admin/", permanent=False)),
    path("django-admin/", admin.site.urls),
    path("favicon.ico", RedirectView.as_view(url="/static/img/favicon.ico", permanent=True)),
]

handler400 = "apps.inti.views.galat_400"
handler403 = "apps.inti.views.galat_403"
handler404 = "apps.inti.views.galat_404"
handler500 = "apps.inti.views.galat_500"
