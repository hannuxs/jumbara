from django.urls import path

from . import views_admin as v

app_name = "inti_admin"

urlpatterns = [
    path("pengaturan/", v.pengaturan_form, name="pengaturan"),
    path("log/", v.log_daftar, name="log"),
    path("log/unduh/", v.log_unduh, name="log_unduh"),
    path("cadangan/", v.cadangan_daftar, name="cadangan"),
    path("cadangan/buat/", v.cadangan_buat, name="cadangan_buat"),
    path("cadangan/unduh/<str:nama>/", v.cadangan_unduh, name="cadangan_unduh"),
]
