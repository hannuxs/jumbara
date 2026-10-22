"""Tes akun, sesi mutlak 2 jam, ganti sandi, dan hak akses per peran."""

from __future__ import annotations

import time

import pytest
from django.contrib.sessions.models import Session
from django.test import Client

from apps.akun.middleware import KUNCI_LOGIN_PADA
from apps.akun.models import SesiAkun
from apps.inti.models import LogAktivitas

from .conftest import SANDI, masuk

RUTE_SUPERADMIN = [
    "/superadmin/",
    "/superadmin/qr-form.png",
    "/superadmin/biodata/",
    "/superadmin/biodata/tambah/",
    "/superadmin/biodata/unduh/umum/",
    "/superadmin/biodata/unduh/lengkap/",
    "/superadmin/sampah/",
    "/superadmin/kontingen/",
    "/superadmin/kontingen/tambah/",
    "/superadmin/akun/",
    "/superadmin/pengaturan/",
    "/superadmin/log/",
    "/superadmin/log/unduh/",
    "/superadmin/cadangan/",
]


def test_masuk_berhasil_dan_tercatat(client, superadmin):
    r = masuk(client, "superadmin")
    assert r.status_code == 302 and r["Location"].startswith("/masuk/lanjut/")
    assert SesiAkun.objects.filter(pengguna=superadmin).count() == 1
    assert LogAktivitas.objects.filter(aksi="akun.masuk").exists()


def test_masuk_gagal_pesan_umum(client, superadmin):
    r1 = masuk(client, "superadmin", "salah")
    r2 = masuk(client, "tidakada", "salah")
    assert "Nama akun atau kata sandi salah." in r1.content.decode()
    assert "Nama akun atau kata sandi salah." in r2.content.decode()


def test_batas_percobaan_masuk(client, superadmin):
    for _ in range(5):
        masuk(client, "superadmin", "salah")
    r = masuk(client, "superadmin")  # sandi benar pun ditahan
    assert r.status_code == 429
    assert not SesiAkun.objects.exists()


def test_sesi_habis_setelah_2_jam_walau_aktif(client, superadmin):
    masuk(client, "superadmin")
    assert client.get("/superadmin/").status_code == 200
    s = client.session
    s[KUNCI_LOGIN_PADA] = int(time.time()) - 2 * 3600 - 1
    s.save()
    r = client.get("/superadmin/")
    assert r.status_code == 302 and r["Location"].startswith("/masuk/")
    # Benar-benar keluar, bukan hanya dialihkan sekali.
    assert client.get("/superadmin/").status_code == 302


def test_sesi_belum_2_jam_tetap_masuk(client, superadmin):
    masuk(client, "superadmin")
    s = client.session
    s[KUNCI_LOGIN_PADA] = int(time.time()) - 2 * 3600 + 120
    s.save()
    assert client.get("/superadmin/").status_code == 200


def test_sesi_habis_api_json_401(client, panitia):
    masuk(client, "panitia")
    s = client.session
    s[KUNCI_LOGIN_PADA] = 0
    s.save()
    r = client.get("/panitia/", HTTP_X_REQUESTED_WITH="XMLHttpRequest")
    assert r.status_code == 401 and r.json()["galat"] == "SESI_HABIS"


def test_ganti_sandi_mengeluarkan_semua_perangkat(superadmin, panitia):
    admin = Client()
    hp1, hp2 = Client(), Client()
    masuk(admin, "superadmin")
    masuk(hp1, "panitia")
    masuk(hp2, "panitia")
    assert hp1.get("/panitia/").status_code == 200
    r = admin.post(
        f"/superadmin/akun/{panitia.pk}/sandi/", {"sandi_baru": "SandiBaru-98765", "ulangi": "SandiBaru-98765"}
    )
    assert r.status_code == 302
    assert hp1.get("/panitia/").status_code == 302
    assert hp2.get("/panitia/").status_code == 302
    assert not SesiAkun.objects.filter(pengguna=panitia).exists()
    assert LogAktivitas.objects.filter(aksi="sandi.diganti").exists()
    # Sandi baru berlaku.
    hp3 = Client()
    assert masuk(hp3, "panitia", "SandiBaru-98765").status_code == 302


def test_ganti_sandi_sendiri_perangkat_ini_tetap_masuk(superadmin):
    a, b = Client(), Client()
    masuk(a, "superadmin")
    masuk(b, "superadmin")
    a.post(f"/superadmin/akun/{superadmin.pk}/sandi/", {"sandi_baru": "SandiBaru-98765", "ulangi": "SandiBaru-98765"})
    assert a.get("/superadmin/").status_code == 200
    assert b.get("/superadmin/").status_code == 302


def test_sandi_lemah_ditolak(klien_superadmin, panitia):
    r = klien_superadmin.post(
        f"/superadmin/akun/{panitia.pk}/sandi/", {"sandi_baru": "1234567890", "ulangi": "1234567890"}
    )
    assert r.status_code == 200 and r.context["form"].errors


def test_keluar_menghapus_sesi(client, superadmin):
    masuk(client, "superadmin")
    client.post("/keluar/")
    assert not SesiAkun.objects.exists()
    assert client.get("/superadmin/").status_code == 302


@pytest.mark.parametrize("url", RUTE_SUPERADMIN)
def test_publik_dialihkan_ke_masuk(client, url):
    r = client.get(url)
    assert r.status_code == 302 and r["Location"].startswith("/masuk/")


@pytest.mark.parametrize("url", RUTE_SUPERADMIN)
@pytest.mark.parametrize("akun", ["panitia", "juri"])
def test_panitia_dan_juri_tidak_bisa_buka_superadmin(client, panitia, juri, akun, url):
    masuk(client, akun)
    assert client.get(url).status_code == 403


@pytest.mark.parametrize("url", RUTE_SUPERADMIN)
def test_superadmin_bisa_buka_semua(klien_superadmin, url):
    r = klien_superadmin.get(url)
    assert r.status_code == 200, url


def test_panitia_tidak_bisa_lihat_nik_dan_foto(client, panitia):
    masuk(client, "panitia")
    assert client.post("/superadmin/biodata/1/nik/").status_code == 403
    assert client.get("/superadmin/biodata/1/foto/").status_code == 403


def test_juri_tidak_bisa_buka_halaman_panitia(client, juri):
    masuk(client, "juri")
    assert client.get("/panitia/").status_code == 403
    assert client.get("/juri/").status_code == 200


def test_admin_django_hanya_superadmin(client, panitia):
    masuk(client, "panitia")
    r = client.get("/django-admin/")
    assert r.status_code == 302


def test_kebersihan_sesi(superadmin):
    c = Client()
    masuk(c, "superadmin")
    Session.objects.all().delete()
    from apps.akun.services import bersihkan_sesi_kedaluwarsa

    assert bersihkan_sesi_kedaluwarsa() == 1


def test_sandi_konstanta():
    assert len(SANDI) >= 10


def test_coop_hanya_lewat_https(client):
    assert "Cross-Origin-Opener-Policy" not in client.get("/")
    r = client.get("/", HTTP_X_FORWARDED_PROTO="https")
    assert r["Cross-Origin-Opener-Policy"] == "same-origin"
