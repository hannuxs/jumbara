from django.urls import path

from . import views_kelola as v

app_name = "anjangsana_admin"

urlpatterns = [
    path("", v.kelola, name="kelola"),
    path("poster.pdf", v.poster, name="poster"),
]
