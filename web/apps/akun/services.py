"""Logika akun: catatan sesi per perangkat, ganti sandi (keluarkan semua perangkat)."""

from __future__ import annotations

import time

from django.contrib.auth import update_session_auth_hash
from django.contrib.sessions.models import Session
from django.db import transaction
from django.utils import timezone

from apps.inti.log import catat
from apps.inti.utils import ip_klien, user_agent

from .middleware import KUNCI_LOGIN_PADA
from .models import Pengguna, SesiAkun

# Halaman awal setiap peran (bila tidak ada menu terakhir yang tersimpan di perangkat).
HALAMAN_AWAL = {
    "SUPERADMIN": "/superadmin/",
    "PANITIA": "/panitia/",
    "JURI": "/juri/",
}

# Awalan rute yang boleh dibuka setiap peran (untuk kembali ke menu terakhir).
AWALAN_RUTE = {
    "SUPERADMIN": ["/superadmin/", "/panitia/", "/juri/"],
    "PANITIA": ["/panitia/"],
    "JURI": ["/juri/"],
}


def catat_login(request, user: Pengguna) -> None:
    """Dipanggil tepat setelah `login()`: simpan jam login dan pemetaan sesi -> akun."""
    request.session[KUNCI_LOGIN_PADA] = int(time.time())
    request.session.save()
    SesiAkun.objects.update_or_create(
        session_key=request.session.session_key,
        defaults={
            "pengguna": user,
            "login_pada": timezone.now(),
            "perangkat_id": getattr(request, "perangkat_id", ""),
            "ip": ip_klien(request),
            "user_agent": user_agent(request),
        },
    )
    catat(request, "akun.masuk", user, keterangan=f"Masuk sebagai {user.username}")


def hapus_catatan_sesi(session_key: str | None) -> None:
    if session_key:
        SesiAkun.objects.filter(session_key=session_key).delete()


def keluarkan_semua(user: Pengguna, kecuali_session_key: str | None = None) -> int:
    """Hapus semua sesi milik akun (semua perangkat langsung keluar). Mengembalikan jumlahnya."""
    kunci = list(
        SesiAkun.objects.filter(pengguna=user).exclude(session_key=kecuali_session_key or "")
        .values_list("session_key", flat=True)
    )  # fmt: skip
    Session.objects.filter(session_key__in=kunci).delete()
    SesiAkun.objects.filter(session_key__in=kunci).delete()
    return len(kunci)


@transaction.atomic
def ganti_sandi(request, user: Pengguna, sandi_baru: str) -> int:
    """Ganti kata sandi akun dan keluarkan semua perangkat yang memakainya.

    Jika superadmin mengganti sandinya sendiri, perangkat yang sedang dipakai tetap masuk.
    """
    user.set_password(sandi_baru)
    user.sandi_diganti_pada = timezone.now()
    user.wajib_ganti_sandi = False
    user.save(update_fields=["password", "sandi_diganti_pada", "wajib_ganti_sandi"])
    sendiri = request.user.pk == user.pk
    jumlah = keluarkan_semua(user, kecuali_session_key=request.session.session_key if sendiri else None)
    if sendiri:
        update_session_auth_hash(request, user)
    catat(
        request, "sandi.diganti", user, keterangan=f"Sandi akun {user.username} diganti; {jumlah} perangkat dikeluarkan"
    )
    return jumlah


def bersihkan_sesi_kedaluwarsa() -> int:
    """Hapus catatan SesiAkun yang sesinya sudah tidak ada atau sudah lewat 2 jam."""
    ada = set(Session.objects.filter(expire_date__gt=timezone.now()).values_list("session_key", flat=True))
    lama = SesiAkun.objects.exclude(session_key__in=ada)
    jumlah = lama.count()
    lama.delete()
    return jumlah
