"""Setel ulang kata sandi akun dari komputer server (bila sandi lupa atau .env diubah).

Sandi di web\\.env (SIGAP_SANDI_AWAL_*) hanya dipakai sekali saat sigap_seed membuat akun.
Mengubah .env sesudahnya TIDAK mengubah sandi di database; pakai perintah ini.

    python manage.py sigap_atur_sandi superadmin            (ketik sandi baru, tidak tampil di layar)
    python manage.py sigap_atur_sandi --semua --dari-env    (ketiga akun memakai SIGAP_SANDI_AWAL_* di .env)

Akun wajib mengganti sandi saat masuk berikutnya, semua perangkat yang memakainya dikeluarkan,
dan tindakan dicatat di log aktivitas.
"""

from __future__ import annotations

import getpass

import environ
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.akun.models import Pengguna
from apps.akun.services import keluarkan_semua
from apps.inti.log import catat


class Command(BaseCommand):
    help = "Setel ulang kata sandi akun (superadmin/panitia/juri) dari server."

    def add_arguments(self, parser):
        parser.add_argument("akun", nargs="*", help="Nama akun, misalnya superadmin panitia juri.")
        parser.add_argument("--semua", action="store_true", help="Semua akun.")
        parser.add_argument("--dari-env", action="store_true", help="Pakai SIGAP_SANDI_AWAL_<PERAN> dari web\\.env.")

    def handle(self, *args, **o):
        qs = Pengguna.objects.all() if o["semua"] else Pengguna.objects.filter(username__in=o["akun"])
        akun = list(qs.order_by("username"))
        if not akun:
            raise CommandError("Sebutkan nama akun (superadmin, panitia, juri) atau --semua.")
        tidak_ada = set(o["akun"]) - {a.username for a in akun}
        if tidak_ada:
            raise CommandError(f"Akun tidak ditemukan: {', '.join(sorted(tidak_ada))}")
        env = environ.Env()
        if o["dari_env"]:
            environ.Env.read_env(settings.BASE_DIR / ".env", overwrite=True)
        for a in akun:
            if o["dari_env"]:
                kunci = f"SIGAP_SANDI_AWAL_{a.peran}"
                sandi = env(kunci, default="") or ""
                if not sandi:
                    raise CommandError(f"{kunci} kosong di web\\.env.")
            else:
                sandi = getpass.getpass(f"Sandi baru untuk {a.username}: ")
                if sandi != getpass.getpass("Ulangi sandi: "):
                    raise CommandError("Sandi tidak sama. Tidak ada yang diubah.")
                if not sandi:
                    raise CommandError("Sandi tidak boleh kosong.")
            with transaction.atomic():
                a.set_password(sandi)
                a.wajib_ganti_sandi = True
                a.sandi_diganti_pada = timezone.now()
                a.is_active = True
                a.save(update_fields=["password", "wajib_ganti_sandi", "sandi_diganti_pada", "is_active"])
                n = keluarkan_semua(a)
                catat(
                    None,
                    "sandi.direset",
                    a,
                    keterangan=f"Sandi akun {a.username} disetel ulang dari server; {n} perangkat dikeluarkan",
                )
            pendek = "  (PENDEK: ganti dengan sandi kuat saat masuk)" if len(sandi) < 10 else ""
            self.stdout.write(self.style.SUCCESS(f"Sandi {a.username} disetel ulang. Wajib ganti saat masuk.{pendek}"))
