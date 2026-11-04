"""Poin daftar ulang (R15): tepat waktu = 1, telat = 0,5 (bisa diubah di pengaturan).

Masalah antrean: kontingen yang datang tepat waktu bisa tertahan antrean panjang sehingga anggota di belakang
baru dipindai setelah batas. Penyelesaiannya, ketepatan waktu dinilai dari WAKTU TIBA KONTINGEN:
- Waktu tiba = saat panitia memindai QR kontingen di ujung antrean, atau (bila tidak) saat kartu anggota pertama
  kontingen itu dipindai. Yang paling awal dipakai.
- Seseorang dihitung tepat waktu bila ia sendiri dipindai sampai batas, ATAU kontingennya tiba sampai batas dan ia
  dipindai paling lambat batas + toleransi antrean (bawaan 120 menit). Orang yang datang sendiri jauh setelah
  rombongannya tetap dihitung telat.
- Superadmin bisa mengoreksi per orang (tepat/telat, dengan alasan) dan mengisi waktu tiba kontingen secara manual.
Tidak ada pengurangan poin untuk yang belum daftar ulang (hanya poin positif).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.inti import pengaturan

from .models import KedatanganKontingen, Kehadiran, SumberKedatangan, TitikAbsen

KODE_DAFTAR_ULANG = "daftar-ulang"


def adalah_daftar_ulang(titik: TitikAbsen) -> bool:
    return bool(titik.kegiatan_id and titik.kegiatan.kode == KODE_DAFTAR_ULANG)


def _angka(kunci: str, bawaan: float) -> float:
    try:
        return float(str(pengaturan.ambil(kunci, bawaan)).replace(",", "."))
    except (TypeError, ValueError):
        return bawaan


def poin_tepat() -> float:
    return _angka("daftar_ulang.poin_tepat", 1)


def poin_telat() -> float:
    return _angka("daftar_ulang.poin_telat", 0.5)


def toleransi() -> timedelta:
    return timedelta(minutes=max(0, int(_angka("daftar_ulang.toleransi_antrean_menit", 120))))


def batas(titik: TitikAbsen) -> datetime:
    """Batas tepat waktu: pengaturan daftar_ulang.batas_tepat (JJ:MM) atau jam selesai titik (bawaan 12.00)."""
    teks = str(pengaturan.ambil("daftar_ulang.batas_tepat") or "").strip().replace(".", ":")
    jam = titik.selesai or time(12, 0)
    if teks:
        try:
            j, m = teks.split(":")[:2]
            jam = time(int(j), int(m))
        except ValueError:
            pass
    return timezone.make_aware(datetime.combine(titik.tanggal, jam), timezone.get_current_timezone())


def catat_kedatangan(titik: TitikAbsen, kontingen, pada: datetime, sumber: str, nama: str = "", client_uuid=None):
    """Simpan waktu tiba kontingen (idempoten). Bila sudah ada, waktu yang lebih awal yang dipakai.

    Mengembalikan (kedatangan, baru)."""
    try:
        with transaction.atomic():
            return KedatanganKontingen.objects.create(
                titik_absen=titik, kontingen=kontingen, tiba_pada=pada, sumber=sumber, nama_pemindai=nama[:100],
                client_uuid=client_uuid,
            ), True  # fmt: skip
    except IntegrityError:
        ada = KedatanganKontingen.objects.filter(titik_absen=titik, kontingen=kontingen).first()
        if ada is None:  # client_uuid sama dari kiriman ulang, baris kontingen lain (tidak mungkin dari HP)
            ada = KedatanganKontingen.objects.get(client_uuid=client_uuid)
            return ada, False
        if pada < ada.tiba_pada and sumber != SumberKedatangan.MANUAL:
            # Pindaian dari antrean offline bisa datang belakangan dengan jam lebih awal.
            KedatanganKontingen.objects.filter(pk=ada.pk, tiba_pada__gt=pada).update(tiba_pada=pada, sumber=sumber)
            ada.refresh_from_db()
        return ada, False


def tepat_waktu(k: Kehadiran, tiba_kontingen: datetime | None, batas_dt: datetime, tol: timedelta) -> bool:
    if k.tepat_waktu_manual is not None:
        return k.tepat_waktu_manual
    if k.dipindai_pada <= batas_dt:
        return True
    return tiba_kontingen is not None and tiba_kontingen <= batas_dt and k.dipindai_pada <= batas_dt + tol


@dataclass
class RingkasDaftarUlang:
    tiba: KedatanganKontingen | None
    tepat: int = 0
    telat: int = 0

    @property
    def hadir(self) -> int:
        return self.tepat + self.telat

    @property
    def poin(self) -> float:
        # Decimal agar 0,5 + 0,5 + ... tidak menimbulkan sisa pecahan biner.
        hasil = Decimal(str(poin_tepat())) * self.tepat + Decimal(str(poin_telat())) * self.telat
        return float(hasil)


def ringkas_per_kontingen(titik_list: list[TitikAbsen]) -> dict[int, RingkasDaftarUlang]:
    """{kontingen_id: RingkasDaftarUlang} untuk semua titik daftar ulang yang diberikan."""
    hasil: dict[int, RingkasDaftarUlang] = {}
    tol = toleransi()
    for t in titik_list:
        b = batas(t)
        tiba = {x.kontingen_id: x for x in KedatanganKontingen.objects.filter(titik_absen=t)}
        for k in Kehadiran.objects.filter(titik_absen=t).select_related("peserta"):
            kid = k.peserta.kontingen_id
            r = hasil.setdefault(kid, RingkasDaftarUlang(tiba.get(kid)))
            if r.tiba is None:
                r.tiba = tiba.get(kid)
            if tepat_waktu(k, tiba[kid].tiba_pada if kid in tiba else None, b, tol):
                r.tepat += 1
            else:
                r.telat += 1
    return hasil


def status_per_orang(titik: TitikAbsen, hadir: list[Kehadiran]) -> None:
    """Tandai setiap kehadiran daftar ulang dengan .tepat_waktu dan .otomatis (untuk halaman superadmin)."""
    b, tol = batas(titik), toleransi()
    tiba = {x.kontingen_id: x.tiba_pada for x in KedatanganKontingen.objects.filter(titik_absen=titik)}
    for k in hadir:
        k.tepat_waktu = tepat_waktu(k, tiba.get(k.peserta.kontingen_id), b, tol)
        k.otomatis = k.tepat_waktu_manual is None
