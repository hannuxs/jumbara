from django.urls import path

from . import views_admin as v

app_name = "akun_admin"

urlpatterns = [
    path("", v.daftar, name="daftar"),
    path("<int:pk>/sandi/", v.ubah_sandi, name="sandi"),
    path("<int:pk>/nama/", v.ubah_nama, name="nama"),
    path("<int:pk>/keluarkan/", v.keluarkan, name="keluarkan"),
]
