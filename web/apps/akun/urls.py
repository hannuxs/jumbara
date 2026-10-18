from django.urls import path

from . import views

app_name = "akun"

urlpatterns = [
    path("masuk/", views.masuk, name="masuk"),
    path("masuk/lanjut/", views.lanjut, name="lanjut"),
    path("keluar/", views.keluar, name="keluar"),
    path("panitia/", views.panitia_awal, name="panitia"),
    path("juri/", views.juri_awal, name="juri"),
]
