"""python manage.py sigap_jadwal: dijalankan Windows Task Scheduler setiap menit.

Memeriksa tugas yang jatuh tempo lalu menjalankannya:
- cadangan harian pukul 02.00 WITA,
- cadangan setiap 3 jam selama hari acara (bawaan 12-15 November 2026),
- bersih-bersih sesi kedaluwarsa (sekali sehari).
"""

from __future__ import annotations

from datetime import date, timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.inti import cadangan, pengaturan
from apps.inti.log import catat

JAM_HARIAN = 2
INTERVAL_ACARA = timedelta(hours=3)


class Command(BaseCommand):
    help = "Menjalankan tugas terjadwal yang jatuh tempo (cadangan, bersih-bersih)."

    def add_arguments(self, parser):
        parser.add_argument("--paksa-cadangan", action="store_true", help="Buat cadangan sekarang juga")

    def handle(self, *args, **opsi):
        sekarang = timezone.localtime()
        nilai = pengaturan.semua()
        terakhir = pengaturan.ke_datetime(nilai.get("jadwal.cadangan_terakhir"))
        harian_terakhir = nilai.get("jadwal.cadangan_harian_tanggal") or ""

        alasan = ""
        if opsi["paksa_cadangan"]:
            alasan = "manual-perintah"
        elif sekarang.hour >= JAM_HARIAN and harian_terakhir != sekarang.date().isoformat():
            alasan = "harian"
        elif self._hari_acara(sekarang.date(), nilai) and (terakhir is None or sekarang - terakhir >= INTERVAL_ACARA):
            alasan = "acara"

        if alasan:
            try:
                info = cadangan.buat(alasan)
            except cadangan.GagalCadangan as e:
                catat(None, "cadangan.gagal", keterangan=str(e)[:255])
                self.stderr.write(self.style.ERROR(f"Cadangan gagal: {e}"))
            else:
                pengaturan.simpan("jadwal.cadangan_terakhir", sekarang.isoformat(), "sigap_jadwal")
                if alasan == "harian":
                    pengaturan.simpan("jadwal.cadangan_harian_tanggal", sekarang.date().isoformat(), "sigap_jadwal")
                catat(None, "cadangan.dibuat", keterangan=f"{info.nama} ({info.ukuran // 1024} KB, {alasan})")
                self.stdout.write(self.style.SUCCESS(f"Cadangan dibuat: {info.path}"))

        if nilai.get("jadwal.bersih_tanggal") != sekarang.date().isoformat():
            from apps.akun.services import bersihkan_sesi_kedaluwarsa

            call_command("clearsessions")
            jumlah = bersihkan_sesi_kedaluwarsa()
            pengaturan.simpan("jadwal.bersih_tanggal", sekarang.date().isoformat(), "sigap_jadwal")
            self.stdout.write(f"Bersih-bersih sesi selesai ({jumlah} catatan sesi dihapus).")

    @staticmethod
    def _hari_acara(hari: date, nilai: dict) -> bool:
        try:
            mulai = date.fromisoformat(nilai.get("jadwal.acara_mulai") or "2026-11-12")
            selesai = date.fromisoformat(nilai.get("jadwal.acara_selesai") or "2026-11-15")
        except ValueError:
            return False
        return mulai <= hari <= selesai
