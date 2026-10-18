"""NIK: enkripsi (Fernet), hash HMAC untuk cek dobel, penyamaran, dan cek isi NIK.

NIK tidak pernah disimpan dalam teks biasa di database. Kolom `nik_hash` (HMAC-SHA256 dengan
kunci aplikasi) bersifat UNIQUE untuk data aktif sehingga NIK dobel ditolak database.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import date
from functools import lru_cache

from cryptography.fernet import Fernet, MultiFernet
from django.conf import settings


@lru_cache(maxsize=1)
def _fernet() -> MultiFernet:
    kunci = [k.strip() for k in settings.SIGAP_KUNCI_NIK if k.strip()]
    if not kunci:
        raise RuntimeError("SIGAP_KUNCI_NIK belum diisi di web\\.env")
    return MultiFernet([Fernet(k.encode()) for k in kunci])


def enkripsi(nik: str) -> str:
    return _fernet().encrypt(nik.encode()).decode()


def dekripsi(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


def hash_nik(nik: str) -> str:
    kunci = settings.SIGAP_KUNCI_HASH_NIK
    if not kunci:
        raise RuntimeError("SIGAP_KUNCI_HASH_NIK belum diisi di web\\.env")
    return hmac.new(kunci.encode(), nik.encode(), hashlib.sha256).hexdigest()


def samarkan(nik: str) -> str:
    """Contoh: 6501********0003."""
    if len(nik) != 16:
        return "*" * len(nik)
    return f"{nik[:4]}{'*' * 8}{nik[-4:]}"


def format_valid(nik: str) -> bool:
    return len(nik) == 16 and nik.isdigit() and len(set(nik)) > 1


def info_dari_nik(nik: str) -> tuple[int, int, int, str] | None:
    """(tanggal, bulan, dua digit tahun, jenis kelamin 'L'/'P') dari digit 7-12 NIK."""
    if not format_valid(nik):
        return None
    tgl = int(nik[6:8])
    bln = int(nik[8:10])
    thn = int(nik[10:12])
    jk = "L"
    if tgl > 40:
        tgl -= 40
        jk = "P"
    return tgl, bln, thn, jk


def cocok_tanggal_lahir(nik: str, tanggal_lahir: date) -> bool:
    info = info_dari_nik(nik)
    if info is None:
        return False
    tgl, bln, thn, _ = info
    return (tgl, bln, thn) == (tanggal_lahir.day, tanggal_lahir.month, tanggal_lahir.year % 100)


def cocok_jenis_kelamin(nik: str, jenis_kelamin: str) -> bool:
    info = info_dari_nik(nik)
    if info is None:
        return False
    return info[3] == jenis_kelamin
