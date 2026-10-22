from django.urls import path

from . import views_rekap as v

app_name = "rekap"

urlpatterns = [
    path("", v.beranda, name="tingkat"),
    path("titik/<int:pk>/", v.titik, name="titik"),
    path("kegiatan/", v.kegiatan_daftar, name="kegiatan_daftar"),
    path("kegiatan/<int:pk>/", v.kegiatan, name="kegiatan"),
    path("kontingen/", v.kontingen_daftar, name="kontingen_daftar"),
    path("kontingen/<int:pk>/", v.kontingen, name="kontingen"),
    path("orang/", v.orang, name="orang"),
    path("orang/<int:pk>/", v.orang, name="orang_detail"),
    path("harian/", v.harian, name="harian"),
    path("daftar-ulang/", v.daftar_ulang, name="daftar_ulang"),
]
