from django.urls import path

from . import views_kelola as v

app_name = "anjangsana_kelola"

urlpatterns = [
    path("", v.peringkat, name="peringkat"),
    path("kunjungan/", v.kunjungan, name="kunjungan"),
    path("review/", v.review, name="review"),
    path("review/<int:pk>/hapus/", v.review_hapus, name="review_hapus"),
]
