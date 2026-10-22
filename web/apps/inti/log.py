"""Pencatatan log aktivitas. Dipanggil dari services setiap kali data berubah."""

from __future__ import annotations

import logging
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from django.db import models

from .models import LogAktivitas
from .utils import ip_klien, user_agent

logger = logging.getLogger("sigap")

# Kolom yang tidak boleh masuk log apa adanya.
KOLOM_RAHASIA = {"password", "nik", "nik_terenkripsi", "nik_hash", "qr_token", "foto_path"}


def _bersihkan(nilai: Any) -> Any:
    if isinstance(nilai, dict):
        return {k: ("***" if k in KOLOM_RAHASIA else _bersihkan(v)) for k, v in nilai.items()}
    if isinstance(nilai, list | tuple):
        return [_bersihkan(v) for v in nilai]
    if isinstance(nilai, datetime | date | time):
        return nilai.isoformat()
    if isinstance(nilai, Decimal):
        return str(nilai)
    if isinstance(nilai, models.Model):
        return str(nilai.pk)
    return nilai


def catat(
    request,
    aksi: str,
    subjek: models.Model | None = None,
    keterangan: str = "",
    lama: dict | None = None,
    baru: dict | None = None,
    nama_pelaku: str | None = None,
) -> LogAktivitas:
    """Simpan satu baris log. `request` boleh None (perintah manajemen)."""
    pengguna = None
    peran = ""
    ip = None
    ua = ""
    perangkat = ""
    if request is not None:
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            pengguna = user
            peran = getattr(user, "peran", "")
        ip = ip_klien(request)
        ua = user_agent(request)
        perangkat = getattr(request, "perangkat_id", "")
        if nama_pelaku is None:
            nama_pelaku = getattr(request, "nama_pelaku", "")
    else:
        peran = "SISTEM"
    return LogAktivitas.objects.create(
        pengguna=pengguna,
        peran=peran or "PUBLIK",
        nama_pelaku=(nama_pelaku or "")[:100],
        aksi=aksi,
        subjek_tipe=subjek._meta.model_name if subjek is not None else "",
        subjek_id=str(subjek.pk) if subjek is not None else "",
        keterangan=keterangan[:255],
        data_lama=_bersihkan(lama) if lama else None,
        data_baru=_bersihkan(baru) if baru else None,
        ip=ip,
        user_agent=ua,
        perangkat_id=perangkat[:64],
    )


def selisih(lama: dict, baru: dict) -> tuple[dict, dict]:
    """Ambil hanya kolom yang berubah."""
    kunci = [k for k in baru if lama.get(k) != baru.get(k)]
    return {k: lama.get(k) for k in kunci}, {k: baru.get(k) for k in kunci}
