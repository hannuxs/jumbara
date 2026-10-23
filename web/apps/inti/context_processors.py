"""Variabel yang tersedia di semua template."""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.akun.middleware import sisa_detik

from . import pengaturan
from .utils import tautan_wa

# (grup, [(kode menu, label, url)]). Menu tahap berikutnya ditambahkan saat fiturnya selesai.
MENU_SUPERADMIN = [
    ("Biodata", [
        ("dasbor", "Dasbor", "/superadmin/"),
        ("biodata", "Daftar biodata", "/superadmin/biodata/"),
        ("tambah", "Tambah biodata", "/superadmin/biodata/tambah/"),
        ("kontingen", "Kontingen dan kuota", "/superadmin/kontingen/"),
        ("sampah", "Tempat sampah", "/superadmin/sampah/"),
    ]),
    ("Kartu", [
        ("kartu", "Kartu dan QR kontingen", "/superadmin/kartu/"),
    ]),
    ("Absensi", [
        ("pantauan", "Pantauan langsung", "/superadmin/absensi/pantauan/"),
        ("titik", "Titik absen", "/superadmin/absensi/titik/"),
        ("pindai", "Buka pemindai", "/panitia/"),
        ("rekap", "Rekap dan poin", "/rekap/"),
        ("kegiatan_kuota", "Kegiatan dan kuota", "/superadmin/absensi/kegiatan/"),
    ]),
    ("Penilaian", [
        ("form", "Form dan penilaian", "/superadmin/form/"),
        ("juri", "Halaman juri", "/juri/"),
        ("piagam", "Piagam", "/superadmin/piagam/"),
    ]),
    ("Anjangsana", [
        ("anjangsana", "Sesi, status, poster", "/superadmin/anjangsana/"),
        ("anjangsana_peringkat", "Peringkat dan review", "/rekap/anjangsana/"),
    ]),
    ("Pengaturan", [
        ("pengaturan", "Pengaturan form", "/superadmin/pengaturan/"),
        ("akun", "Akun dan kata sandi", "/superadmin/akun/"),
    ]),
    ("Keamanan", [
        ("log", "Log aktivitas", "/superadmin/log/"),
        ("cadangan", "Cadangan data", "/superadmin/cadangan/"),
    ]),
]  # fmt: skip


def sigap(request) -> dict:
    nilai = pengaturan.untuk_request(request)
    wa = nilai.get("kontak.superadmin_wa", "")
    data = {
        "SIGAP_URL": settings.SIGAP_URL,
        "kontak_nama": nilai.get("kontak.superadmin_nama") or "Superadmin",
        "kontak_wa": wa,
        "tautan_wa_superadmin": tautan_wa(wa, "Halo Superadmin SIGAP JUMBARA, saya ingin bertanya tentang biodata."),
        "pengumuman": nilai.get("pengumuman.teks", ""),
    }
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated and getattr(user, "superadmin", False):
        data["menu_superadmin"] = MENU_SUPERADMIN
    if user is not None and user.is_authenticated:
        sisa = sisa_detik(request)
        if sisa is not None and sisa > 0:
            data["sesi_sisa_detik"] = sisa
            berakhir = timezone.localtime() + timedelta(seconds=sisa)
            data["sesi_berakhir_jam"] = f"{berakhir:%H.%M} WITA"
    return data
