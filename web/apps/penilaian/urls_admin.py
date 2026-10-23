from django.urls import path

from . import views_admin as v

app_name = "penilaian_admin"

urlpatterns = [
    path("", v.daftar, name="daftar"),
    path("tambah/", v.pengaturan, name="tambah"),
    path("<int:pk>/", v.detail, name="detail"),
    path("<int:pk>/pengaturan/", v.pengaturan, name="ubah"),
    path("<int:pk>/status/", v.status, name="status"),
    path("<int:pk>/salin/", v.salin, name="salin"),
    path("<int:pk>/hapus/", v.hapus, name="hapus"),
    path("<int:pk>/kunci/", v.kunci, name="kunci"),
    path("<int:pk>/pratinjau/", v.pratinjau, name="pratinjau"),
    path("<int:pk>/hasil/", v.hasil, name="hasil"),
    path("<int:pk>/kolom/tambah/", v.kolom_form, name="kolom_tambah"),
    path("<int:pk>/kolom/<int:kid>/", v.kolom_form, name="kolom_ubah"),
    path("<int:pk>/kolom/<int:kid>/hapus/", v.kolom_hapus, name="kolom_hapus"),
    path("<int:pk>/kolom/urutan/", v.kolom_urutan, name="kolom_urutan"),
    path("<int:pk>/rumus/cek/", v.rumus_cek, name="rumus_cek"),
    path("<int:pk>/kiriman/<int:xid>/", v.kiriman_detail, name="kiriman"),
    path("<int:pk>/kiriman/<int:xid>/berkas/<str:kode>/", v.berkas, name="berkas"),
]
