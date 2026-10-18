"""python manage.py sigap_seed: isi data awal (akun, kontingen, kegiatan, titik absen, dll.)."""

from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.inti import seed
from sigap.settings import env


class Command(BaseCommand):
    help = "Mengisi data awal dari folder data/ (aman dijalankan berulang)."

    def add_arguments(self, parser):
        parser.add_argument("--folder-data", default=None, help="Folder CSV (bawaan: ../data)")

    def handle(self, *args, **opsi):
        call_command("createcachetable", verbosity=0)
        folder = Path(opsi["folder_data"]) if opsi["folder_data"] else None
        for baris in seed.jalankan(env, folder):
            self.stdout.write(f"- {baris}")
        self.stdout.write(self.style.SUCCESS("Selesai."))
