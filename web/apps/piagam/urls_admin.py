from django.urls import path

from . import views_admin as v

app_name = "piagam_admin"

urlpatterns = [
    path("", v.beranda, name="beranda"),
    path("pengecualian/", v.pengecualian, name="pengecualian"),
    path("kontingen/<int:pk>/", v.kontingen, name="kontingen"),
    path("kontingen/<int:pk>/unduh.pdf", v.unduh_kontingen, name="unduh_kontingen"),
    path("peserta/<int:pk>/unduh.pdf", v.unduh_peserta, name="unduh_peserta"),
    path("semua.zip", v.unduh_semua, name="unduh_semua"),
    path("terbit/<int:pk>/unduh.pdf", v.unduh_terbit, name="unduh_terbit"),
    path("juara/form/<int:pk>/", v.juara_form, name="juara_form"),
    path("juara/anjangsana/", v.juara_anjangsana, name="juara_anjangsana"),
    path("juara/<str:sumber>/unduh.pdf", v.juara_sumber, name="juara_sumber"),
    path("template/tambah/", v.template, name="template_tambah"),
    path("template/<int:pk>/", v.template, name="template"),
    path("template/<int:pk>/elemen/", v.template_elemen, name="template_elemen"),
    path("template/<int:pk>/pratinjau.png", v.template_pratinjau, name="template_pratinjau"),
    path("template/<int:pk>/pratinjau.pdf", v.template_pratinjau_pdf, name="template_pratinjau_pdf"),
    path("template/<int:pk>/hapus/", v.template_hapus, name="template_hapus"),
]
