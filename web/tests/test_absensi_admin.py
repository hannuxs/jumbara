"""Tes superadmin absensi: kelola titik absen, batalkan/tambah kehadiran, pantauan langsung."""

from __future__ import annotations

from datetime import time

import pytest
from django.test import Client
from django.utils import timezone

from apps.absensi.models import Kehadiran, TitikAbsen
from apps.inti.models import LogAktivitas

from .conftest import masuk
from .test_absensi import buat_peserta, buat_titik, kirim


def data_titik(**ubah):
    data = {
        "kode": "ta-500", "nama_tampil": "Uji Titik", "kegiatan": "", "tingkat": "MADYA",
        "tanggal": timezone.localdate().isoformat(), "mulai": "08:00", "selesai": "10:00",
        "lokasi": "Tenda", "status": "OTOMATIS", "hitung_poin": "on", "catatan": "",
    }  # fmt: skip
    data.update(ubah)
    return data


def test_tambah_ubah_status_titik(klien_superadmin):
    r = klien_superadmin.post("/superadmin/absensi/titik/tambah/", data_titik())
    t = TitikAbsen.objects.get(kode="TA-500")
    assert r.status_code == 302 and t.hitung_poin
    assert LogAktivitas.objects.filter(aksi="titik_absen.dibuat").exists()
    klien_superadmin.post(f"/superadmin/absensi/titik/{t.pk}/ubah/", data_titik(lokasi="Panggung"))
    assert LogAktivitas.objects.get(aksi="titik_absen.diubah").data_baru == {"lokasi": "Panggung"}
    klien_superadmin.post(
        f"/superadmin/absensi/titik/{t.pk}/status/", {"status": "TUTUP", "kembali": "https://jahat.com/"}
    )
    t.refresh_from_db()
    assert t.status == "TUTUP"


def test_validasi_titik(klien_superadmin):
    buat_titik("TA-500")
    r = klien_superadmin.post("/superadmin/absensi/titik/tambah/", data_titik(selesai="07:00"))
    galat = r.context["form"].errors
    assert "kode" in galat and "selesai" in galat


def test_salin_titik(klien_superadmin):
    t = buat_titik("TA-010")
    klien_superadmin.post(f"/superadmin/absensi/titik/{t.pk}/salin/", {"tanggal": "2026-11-14"})
    baru = TitikAbsen.objects.exclude(pk=t.pk).get()
    assert baru.kode == "TA-011" and baru.tanggal.isoformat() == "2026-11-14" and baru.mulai == t.mulai


def test_hapus_titik_hanya_bila_kosong(klien_superadmin, panitia, kontingen_madya):
    t = buat_titik()
    p = buat_peserta(kontingen_madya)
    kirim(panitia, t, "SJP:" + p.qr_token)
    klien_superadmin.post(f"/superadmin/absensi/titik/{t.pk}/hapus/")
    assert TitikAbsen.objects.filter(pk=t.pk).exists()
    t2 = buat_titik("TA-902")
    klien_superadmin.post(f"/superadmin/absensi/titik/{t2.pk}/hapus/")
    assert not TitikAbsen.objects.filter(pk=t2.pk).exists()


def test_batalkan_lalu_pindai_lagi(klien_superadmin, panitia, kontingen_madya):
    t = buat_titik()
    p = buat_peserta(kontingen_madya)
    kirim(panitia, t, "SJP:" + p.qr_token)
    k = Kehadiran.objects.get()
    klien_superadmin.post(f"/superadmin/absensi/kehadiran/{k.pk}/batal/")
    assert not Kehadiran.objects.exists() and Kehadiran.semua.count() == 1
    assert LogAktivitas.objects.filter(aksi="kehadiran.dibatalkan").exists()
    assert kirim(panitia, t, "SJP:" + p.qr_token).status == "HIJAU"  # unik hanya untuk data aktif
    assert Kehadiran.objects.count() == 1


def test_tambah_manual_superadmin(klien_superadmin, kontingen_madya, kontingen_wira):
    t = buat_titik(tingkat="MADYA", status="TUTUP")
    p = buat_peserta(kontingen_madya)
    w = buat_peserta(kontingen_wira, "ORANG WIRA")
    klien_superadmin.post(f"/superadmin/absensi/titik/{t.pk}/tambah-manual/", {"peserta": p.pk, "alasan": "x"})
    assert not Kehadiran.objects.exists()  # alasan wajib
    klien_superadmin.post(
        f"/superadmin/absensi/titik/{t.pk}/tambah-manual/", {"peserta": p.pk, "alasan": "Kartu tertinggal"}
    )
    k = Kehadiran.objects.get()
    assert k.metode == "MANUAL" and k.alasan_manual == "Kartu tertinggal" and k.nama_pemindai == "Penguji"
    klien_superadmin.post(
        f"/superadmin/absensi/titik/{t.pk}/tambah-manual/", {"peserta": w.pk, "alasan": "Ikut membantu"}
    )
    assert Kehadiran.objects.count() == 1  # tingkat beda ditolak tanpa izin
    klien_superadmin.post(
        f"/superadmin/absensi/titik/{t.pk}/tambah-manual/", {"peserta": w.pk, "alasan": "Ikut membantu", "izinkan": "1"}
    )
    assert Kehadiran.objects.count() == 2
    assert LogAktivitas.objects.filter(aksi="kehadiran.ditambah_manual").count() == 2


def test_halaman_dan_pantauan(klien_superadmin, panitia, kontingen_madya):
    t = buat_titik(status="BUKA", tanggal=timezone.localdate(), mulai=time(0, 0), selesai=time(23, 59))
    p = buat_peserta(kontingen_madya)
    kirim(panitia, t, "SJP:" + p.qr_token)
    kirim(panitia, t, "https://bukan-kartu")
    for url in ("/superadmin/absensi/titik/", f"/superadmin/absensi/titik/{t.pk}/", f"/superadmin/absensi/titik/{t.pk}/?q=ani",
                "/superadmin/absensi/titik/tambah/", "/superadmin/absensi/pantauan/"):  # fmt: skip
        assert klien_superadmin.get(url).status_code == 200, url
    d = klien_superadmin.get("/superadmin/absensi/pantauan/data/").json()
    item = next(x for x in d["titik"] if x["id"] == t.pk)
    assert item["hadir"] == 1 and item["hp_aktif"] == 1
    assert d["merah"][0]["kode"] == "QR_ASING"


@pytest.mark.parametrize("url", ["/superadmin/absensi/titik/", "/superadmin/absensi/pantauan/data/"])
def test_panitia_tidak_bisa_kelola(panitia, url):
    c = Client()
    masuk(c, "panitia")
    assert c.get(url).status_code == 403
