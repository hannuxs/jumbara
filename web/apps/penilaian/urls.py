from django.urls import path

from . import views

app_name = "penilaian"

urlpatterns = [
    path("juri/", views.juri_beranda, name="juri"),
    path("juri/<slug:slug>/", views.juri_subjek, name="juri_subjek"),
    path("juri/<slug:slug>/hasil/", views.juri_hasil, name="juri_hasil"),
    path("juri/<slug:slug>/<str:kunci>/", views.juri_isi, name="juri_isi"),
    path("f/<slug:slug>/", views.isi_publik, name="isi_publik"),
    path("f/<slug:slug>/terkirim/", views.terkirim, name="terkirim"),
    path("superadmin/isi/<slug:slug>/", views.isi_admin, name="isi_admin"),
]
