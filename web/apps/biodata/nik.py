"""NIK: enkripsi (Fernet), hash HMAC untuk cek dobel, dan penyamaran.

Isi NIK tidak dicocokkan dengan tanggal lahir atau jenis kelamin (REVISI R4).

NIK tidak pernah disimpan dalam teks biasa di database. Kolom `nik_hash` (HMAC-SHA256 dengan
kunci aplikasi) bersifat UNIQUE untuk data aktif sehingga NIK dobel ditolak database.
"""

from __future__ import annotations

import hashlib
import hmac
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
