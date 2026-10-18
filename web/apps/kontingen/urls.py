from django.urls import path

from . import views

app_name = "kontingen_admin"

urlpatterns = [
    path("", views.daftar, name="daftar"),
    path("tambah/", views.tambah, name="tambah"),
    path("impor-ulang/", views.impor_ulang, name="impor_ulang"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/ubah/", views.ubah, name="ubah"),
    path("<int:pk>/hapus/", views.hapus, name="hapus"),
    path("<int:pk>/pulihkan/", views.pulihkan, name="pulihkan"),
]
