"""Pengaturan aplikasi yang disimpan di database dan bisa diubah superadmin.

Nilai bawaan ada di `BAWAAN`. Baris di tabel `Pengaturan` menimpa nilai bawaan.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import Pengaturan


class StatusPaksa:
    OTOMATIS = "OTOMATIS"
    BUKA = "BUKA"
    TUTUP = "TUTUP"

    PILIHAN = [
        (OTOMATIS, "Otomatis (ikut jadwal)"),
        (BUKA, "Paksa buka"),
        (TUTUP, "Paksa tutup"),
    ]


BAWAAN: dict[str, Any] = {
    "biodata.buka_pada": "2026-10-26T00:00:00+08:00",
    "biodata.tutup_pada": "2026-11-02T23:59:59+08:00",
    "biodata.paksa_status": StatusPaksa.OTOMATIS,
    "biodata.terkunci": False,
    "biodata.waktu_minimal_detik": 10,
    "kontak.superadmin_wa": "",
    "kontak.superadmin_nama": "Superadmin",
    "pengumuman.teks": "",
    "anjangsana.paksa_status": StatusPaksa.OTOMATIS,
    "acara.tanggal_acuan_usia": "2026-11-12",
    "sistem.perawatan": False,
    # Selama hari acara, cadangan dibuat setiap 3 jam.
    "jadwal.acara_mulai": "2026-11-12",
    "jadwal.acara_selesai": "2026-11-15",
    # Ukuran kartu peserta (B-2), bisa disesuaikan bila panitia memakai ukuran sedikit berbeda.
    "kartu.lebar_mm": 88,
    "kartu.tinggi_mm": 125,
    # Titik absen status OTOMATIS terbuka sejak X menit sebelum mulai sampai Y menit setelah selesai.
    "absensi.menit_sebelum": 60,
    "absensi.menit_sesudah": 60,
    # Poin kehadiran: orang di atas kuota tidak menambah poin (docs/15-REKAP-POIN.md).
    "poin.batasi_ke_kuota": True,
    # Pilihan kegiatan di biodata: sesi berjam "08.00-selesai" dianggap selesai pukul ini untuk cek bentrok.
    "kegiatan.selesai_bawaan": "12:00",
    # Piagam (docs/18-PIAGAM.md). {urut} = nomor urut per jenis piagam.
    "piagam.format_nomor_peserta": "{urut}/PST/JUMBARA-V/PMI-BLG/XI/2026",
    "piagam.format_nomor_juara": "{urut}/JR/JUMBARA-V/PMI-BLG/XI/2026",
    "piagam.digit_urut": 3,
    "piagam.tempat": "Tanjung Selor",
    "piagam.tanggal": "2026-11-15",
    "piagam.syarat_daftar_ulang": True,
}


def semua() -> dict[str, Any]:
    """Semua pengaturan (bawaan ditimpa isi database). Satu kueri."""
    hasil = dict(BAWAAN)
    for kunci, nilai in Pengaturan.objects.values_list("kunci", "nilai"):
        hasil[kunci] = nilai
    return hasil


def ambil(kunci: str, bawaan: Any = None) -> Any:
    baris = Pengaturan.objects.filter(kunci=kunci).first()
    if baris is None:
        return BAWAAN.get(kunci, bawaan)
    return baris.nilai


def simpan(kunci: str, nilai: Any, oleh: str = "") -> None:
    Pengaturan.objects.update_or_create(kunci=kunci, defaults={"nilai": nilai, "diubah_oleh": oleh[:100]})


def untuk_request(request) -> dict[str, Any]:
    """Pengaturan yang di-cache per permintaan (dipakai middleware, context processor, view)."""
    if not hasattr(request, "_sigap_pengaturan"):
        request._sigap_pengaturan = semua()
    return request._sigap_pengaturan


def ke_datetime(nilai: Any) -> datetime | None:
    if isinstance(nilai, datetime):
        dt = nilai
    elif isinstance(nilai, str) and nilai:
        dt = parse_datetime(nilai)
    else:
        return None
    if dt is None:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt
