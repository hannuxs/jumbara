from django.urls import path

from . import views_admin as v

app_name = "absensi_admin"

urlpatterns = [
    path("titik/", v.titik_daftar, name="titik_daftar"),
    path("titik/tambah/", v.titik_form, name="titik_tambah"),
    path("titik/<int:pk>/", v.titik_detail, name="titik_detail"),
    path("titik/<int:pk>/ubah/", v.titik_form, name="titik_ubah"),
    path("titik/<int:pk>/status/", v.titik_status, name="titik_status"),
    path("titik/<int:pk>/salin/", v.titik_salin, name="titik_salin"),
    path("titik/<int:pk>/hapus/", v.titik_hapus, name="titik_hapus"),
    path("titik/<int:pk>/tambah-manual/", v.kehadiran_tambah, name="kehadiran_tambah"),
    path("kehadiran/<int:pk>/batal/", v.kehadiran_batal, name="kehadiran_batal"),
    path("kegiatan/", v.kegiatan_daftar, name="kegiatan_daftar"),
    path("kegiatan/<int:pk>/kuota/", v.kegiatan_kuota, name="kegiatan_kuota"),
    path("pantauan/", v.pantauan, name="pantauan"),
    path("pantauan/data/", v.pantauan_json, name="pantauan_json"),
]
