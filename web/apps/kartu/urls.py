from django.urls import path

from . import views as v

app_name = "kartu_admin"

urlpatterns = [
    path("", v.beranda, name="beranda"),
    path("kunci/", v.atur_kunci, name="kunci"),
    path("unduh/semua/", v.unduh_semua, name="unduh_semua"),
    path("unduh/kontingen/<int:pk>/", v.unduh_kontingen, name="unduh_kontingen"),
    path("unduh/peserta/<int:pk>/", v.unduh_peserta, name="unduh_peserta"),
    path("qr/", v.unduh_qr, name="unduh_qr_semua"),
    path("qr/<int:pk>/", v.unduh_qr, name="unduh_qr"),
    path("qr/<int:pk>/ganti/", v.ganti_qr_kontingen, name="ganti_qr"),
    path("tercetak/", v.tandai_tercetak, name="tercetak"),
    path("peserta/<int:pk>/terbitkan-ulang/", v.terbitkan_ulang, name="terbitkan_ulang"),
    path("peserta/<int:pk>/aktif/", v.atur_aktif, name="aktif"),
]
