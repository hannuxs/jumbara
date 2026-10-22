"""python manage.py sigap_cek_lingkungan: periksa kesiapan laptop/server sebelum dipakai."""

from __future__ import annotations

import platform
import sys
import tempfile
from pathlib import Path

import django
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Memeriksa Python, database, folder, kunci, file statis, dan akun."

    def handle(self, *args, **opsi):
        self.gagal = 0
        self.peringatan = 0

        self.judul("Program")
        self.cek(sys.version_info[:2] >= (3, 12), f"Python {platform.python_version()} (butuh 3.12)", wajib=False)
        self.cek(django.VERSION[:2] == (5, 2), f"Django {django.get_version()}")

        self.judul("Database")
        try:
            with connection.cursor() as c:
                c.execute("SELECT VERSION(), @@time_zone, @@character_set_server, @@max_connections, @@sql_mode")
                versi, tz, cs, maxc, mode = c.fetchone()
            angka = tuple(int(x) for x in versi.split("-")[0].split(".")[:2])
            self.cek("mariadb" in versi.lower() and angka >= (10, 5), f"MariaDB {versi} (butuh 10.5+)")
            self.cek(tz in ("+08:00", "SYSTEM"), f"Zona waktu sesi database: {tz}", wajib=False)
            self.cek(cs == "utf8mb4", f"Charset server: {cs}", wajib=False)
            self.cek(int(maxc) >= 200, f"max_connections = {maxc} (disarankan >= 200)", wajib=False)
            self.cek("STRICT_TRANS_TABLES" in mode, "sql_mode berisi STRICT_TRANS_TABLES", wajib=False)
            from django.db.migrations.executor import MigrationExecutor

            belum = MigrationExecutor(connection).migration_plan(
                MigrationExecutor(connection).loader.graph.leaf_nodes()
            )
            self.cek(not belum, f"Migrasi lengkap ({len(belum)} belum diterapkan)")
            tabel = connection.introspection.table_names()
            self.cek("sigap_cache" in tabel, "Tabel cache ada (python manage.py createcachetable)")
        except Exception as e:  # noqa: BLE001
            self.cek(False, f"Tidak bisa terhubung ke database: {e}")
            self.info(
                "MariaDB mati? Laptop: powershell -ExecutionPolicy Bypass -File scripts\\windows\\mariadb-dev.ps1 ; "
                "server: Start-Service MariaDB1011. Periksa juga DB_PORT di .env."
            )

        self.judul("Kunci dan rahasia")
        self.cek(not settings.DEBUG, "DJANGO_DEBUG=False", wajib=False)
        self.cek(
            len(settings.SECRET_KEY) >= 50 and "ganti" not in settings.SECRET_KEY, "DJANGO_SECRET_KEY panjang dan acak"
        )
        try:
            from apps.biodata import nik

            self.cek(nik.dekripsi(nik.enkripsi("1234567890123456")) == "1234567890123456", "SIGAP_KUNCI_NIK valid")
            self.cek(len(settings.SIGAP_KUNCI_HASH_NIK) >= 32, "SIGAP_KUNCI_HASH_NIK terisi (>= 32 karakter)")
        except Exception as e:  # noqa: BLE001
            self.cek(False, f"Kunci NIK bermasalah: {e}")
        self.cek(bool(settings.ALLOWED_HOSTS), f"DJANGO_ALLOWED_HOSTS: {', '.join(settings.ALLOWED_HOSTS)}")
        self.info(f"SIGAP_URL: {settings.SIGAP_URL}")
        if not settings.DEBUG:
            self.cek(settings.SIGAP_URL.startswith("https://"), "SIGAP_URL memakai https://", wajib=False)
            self.cek(bool(settings.CSRF_TRUSTED_ORIGINS), "CSRF_TRUSTED_ORIGINS terisi", wajib=False)

        self.judul("Folder")
        privat = Path(settings.SIGAP_FOLDER_PRIVAT).resolve()
        self.cek_tulis(privat, "Folder privat (foto)")
        self.cek_tulis(Path(settings.SIGAP_FOLDER_CADANGAN), "Folder cadangan")
        self.cek_tulis(Path(settings.FOLDER_LOG), "Folder log")
        static_root = Path(settings.STATIC_ROOT).resolve()
        self.cek(
            static_root not in privat.parents and privat != static_root,
            "Folder privat tidak berada di dalam folder statis",
        )
        self.cek(Path(settings.SIGAP_MYSQLDUMP_PATH).is_file(), f"mysqldump ditemukan: {settings.SIGAP_MYSQLDUMP_PATH}")

        self.judul("File statis")
        self.cek(
            (Path(settings.BASE_DIR) / "static" / "css" / "app.css").is_file(),
            "static/css/app.css sudah dibangun (Tailwind)",
        )
        if not settings.DEBUG:
            self.cek((static_root / "staticfiles.json").is_file(), "collectstatic sudah dijalankan")

        self.judul("Akun dan pengaturan")
        from apps.akun.models import Pengguna
        from apps.inti import pengaturan
        from apps.kontingen.models import Kontingen

        try:
            akun = list(Pengguna.objects.values_list("username", "peran", "wajib_ganti_sandi"))
            self.cek(len(akun) == 3, f"Tiga akun ada ({len(akun)})")
            for username, peran, wajib in akun:
                self.cek(not wajib, f"Sandi akun {username} ({peran}) sudah diganti dari bawaan", wajib=False)
            self.cek(Kontingen.objects.count() >= 29, f"Kontingen: {Kontingen.objects.count()}")
            nilai = pengaturan.semua()
            self.info(
                f"Form biodata: {nilai['biodata.paksa_status']}, buka {nilai['biodata.buka_pada']}, tutup {nilai['biodata.tutup_pada']}"
            )
            self.cek(
                nilai["biodata.paksa_status"] == "OTOMATIS",
                "Status form OTOMATIS (bukan paksa buka/tutup)",
                wajib=False,
            )
            self.cek(bool(nilai.get("kontak.superadmin_wa")), "Nomor WhatsApp superadmin sudah diisi", wajib=False)
        except Exception as e:  # noqa: BLE001
            self.cek(False, f"Tidak bisa membaca akun/pengaturan: {e}")

        self.stdout.write("")
        if self.gagal:
            self.stdout.write(self.style.ERROR(f"{self.gagal} masalah wajib diperbaiki, {self.peringatan} peringatan."))
            sys.exit(1)
        self.stdout.write(self.style.SUCCESS(f"Siap. {self.peringatan} peringatan (lihat tanda !)."))

    def judul(self, teks: str) -> None:
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n{teks}"))

    def info(self, teks: str) -> None:
        self.stdout.write(f"  i {teks}")

    def cek(self, ok: bool, teks: str, wajib: bool = True) -> None:
        if ok:
            self.stdout.write(self.style.SUCCESS(f"  OK {teks}"))
        elif wajib:
            self.gagal += 1
            self.stdout.write(self.style.ERROR(f"  X  {teks}"))
        else:
            self.peringatan += 1
            self.stdout.write(self.style.WARNING(f"  !  {teks}"))

    def cek_tulis(self, folder: Path, nama: str) -> None:
        try:
            folder.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=folder, delete=True):
                pass
            self.cek(True, f"{nama} bisa ditulis: {folder}")
        except OSError as e:
            self.cek(False, f"{nama} tidak bisa ditulis: {folder} ({e})")
