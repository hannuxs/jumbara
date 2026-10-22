from django.urls import path

from . import views

app_name = "anjangsana"

urlpatterns = [
    path("", views.beranda, name="beranda"),
    path("api/kartu", views.api_kartu, name="api_kartu"),
    path("api/tuan-rumah", views.api_tuan_rumah, name="api_tuan_rumah"),
    path("api/kunjungan", views.api_kunjungan, name="api_kunjungan"),
    path("api/review", views.api_review, name="api_review"),
]
