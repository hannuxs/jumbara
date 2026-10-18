from django.urls import path

from . import views_admin as v

app_name = "biodata_admin"

urlpatterns = [
    path("", v.dasbor, name="dasbor"),
    path("qr-form.png", v.qr_form, name="qr_form"),
    path("biodata/", v.daftar, name="daftar"),
    path("biodata/tambah/", v.tambah, name="tambah"),
    path("biodata/unduh/umum/", v.unduh_umum, name="unduh_umum"),
    path("biodata/unduh/lengkap/", v.unduh_lengkap, name="unduh_lengkap"),
    path("biodata/unduh/foto/", v.unduh_foto, name="unduh_foto"),
    path("biodata/<int:pk>/", v.detail, name="detail"),
    path("biodata/<int:pk>/foto/", v.foto, name="foto"),
    path("biodata/<int:pk>/nik/", v.lihat_nik, name="lihat_nik"),
    path("biodata/<int:pk>/ubah/", v.ubah, name="ubah"),
    path("biodata/<int:pk>/hapus/", v.hapus, name="hapus"),
    path("tanda/<int:pk>/abaikan/", v.abaikan_tanda, name="abaikan_tanda"),
    path("sampah/", v.sampah, name="sampah"),
    path("sampah/biodata/<int:pk>/pulihkan/", v.pulihkan, name="pulihkan"),
    path("sampah/biodata/<int:pk>/hapus-permanen/", v.hapus_permanen, name="hapus_permanen"),
]
