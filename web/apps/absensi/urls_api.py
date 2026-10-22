from django.urls import path

from . import api

app_name = "absensi_api"

urlpatterns = [
    path("titik-absen/", api.daftar_titik, name="titik"),
    path("titik-absen/<int:pk>/ringkas/", api.ringkas_titik, name="ringkas"),
    path("titik-absen/<int:pk>/peserta/", api.peserta_ringan, name="peserta_ringan"),
    path("cari-peserta/", api.cari_peserta, name="cari"),
    path("pindai", api.pindai, name="pindai"),
    path("pindai/batch", api.pindai_batch, name="pindai_batch"),
]
