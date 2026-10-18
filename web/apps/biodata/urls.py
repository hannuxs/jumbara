from django.urls import path

from . import views

app_name = "biodata"

urlpatterns = [
    path("", views.beranda, name="beranda"),
    path("daftar/", views.daftar, name="daftar"),
    path("daftar/status/", views.status_json, name="status"),
    path("daftar/bukti/<str:token>/", views.bukti, name="bukti"),
    path("daftar/bukti/<str:token>/pdf/", views.bukti_pdf, name="bukti_pdf"),
]
