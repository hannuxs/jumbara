"""Fixture bersama untuk tes SIGAP JUMBARA (database tes terpisah: sigap_jumbara_test)."""

from __future__ import annotations

import io
import time

import pytest
from django.core import signing
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.akun.models import Pengguna
from apps.akun.models import Peran as PeranAkun
from apps.biodata.forms import SALT_TOKEN
from apps.inti import pengaturan
from apps.kontingen.models import Kontingen

SANDI = "SandiUji-12345"


@pytest.fixture(autouse=True)
def _lingkungan(settings, tmp_path, db):
    """Folder privat sementara, cache bersih, dan form biodata terbuka (paksa buka)."""
    settings.SIGAP_FOLDER_PRIVAT = tmp_path / "privat"
    settings.SIGAP_FOLDER_CADANGAN = tmp_path / "cadangan"
    cache.clear()
    pengaturan.simpan("biodata.paksa_status", "BUKA")
    pengaturan.simpan("biodata.waktu_minimal_detik", 10)
    yield
    cache.clear()


@pytest.fixture
def kontingen_madya(db):
    return Kontingen.objects.create(kode="MA-01", nama="SMP Negeri Uji", tingkat="MADYA", kuota=3)


@pytest.fixture
def kontingen_wira(db):
    return Kontingen.objects.create(kode="WI-01", nama="SMA Negeri Uji", tingkat="WIRA", kuota=30)


def buat_akun(peran: str, username: str) -> Pengguna:
    u = Pengguna(username=username, peran=peran, wajib_ganti_sandi=False)
    if peran == PeranAkun.SUPERADMIN:
        u.is_staff = u.is_superuser = True
    u.set_password(SANDI)
    u.save()
    return u


@pytest.fixture
def superadmin(db):
    return buat_akun(PeranAkun.SUPERADMIN, "superadmin")


@pytest.fixture
def panitia(db):
    return buat_akun(PeranAkun.PANITIA, "panitia")


@pytest.fixture
def juri(db):
    return buat_akun(PeranAkun.JURI, "juri")


def masuk(client, username: str, sandi: str = SANDI):
    return client.post("/masuk/", {"username": username, "password": sandi})


@pytest.fixture
def klien_superadmin(superadmin):
    from django.test import Client

    c = Client()
    masuk(c, "superadmin")
    c.cookies["sigap_nama"] = "Penguji"
    return c


def token_lama(detik: int = 60) -> str:
    """Token kiriman yang seolah dibuat `detik` lalu (lolos cek waktu minimal)."""
    import secrets

    return signing.dumps({"n": secrets.token_hex(16), "t": time.time() - detik}, salt=SALT_TOKEN)


def gambar(format_: str = "JPEG", ukuran=(1200, 900), warna=(200, 120, 90), mode="RGB", exif: bool = False) -> bytes:
    img = Image.new(mode, ukuran, warna)
    buf = io.BytesIO()
    kw = {}
    if exif and format_ == "JPEG":
        e = Image.Exif()
        e[0x010F] = "KameraUji"  # Make
        e[0x0112] = 6  # Orientation: putar 90 derajat
        kw["exif"] = e.tobytes()
    img.save(buf, format=format_, **kw)
    return buf.getvalue()


def file_foto(isi: bytes | None = None, nama: str = "foto.jpg", tipe: str = "image/jpeg") -> SimpleUploadedFile:
    return SimpleUploadedFile(nama, isi if isi is not None else gambar(), content_type=tipe)


# NIK contoh: digit 7-12 = 410112 -> tanggal 1 (perempuan, +40), Januari, 2012.
NIK_PEREMPUAN_2012 = "6501014101120003"


def data_valid(k: Kontingen, **ubah) -> dict:
    data = {
        "kontingen": str(k.pk),
        "tingkat": k.tingkat,
        "peran": "PESERTA",
        "nama_lengkap": "Siti Aminah",
        "nik": NIK_PEREMPUAN_2012,
        "nomor_induk_anggota": "",
        "jenis_kelamin": "P",
        "tempat_lahir": "Tanjung Selor",
        "tanggal_lahir_0": "1",
        "tanggal_lahir_1": "1",
        "tanggal_lahir_2": "2012",
        "alamat": "Jl. Sengkawit RT 05, Tanjung Selor Hilir",
        "golongan_darah": "O",
        "telepon": "",
        "nama_orang_tua": "Budi Santoso",
        "telepon_orang_tua": "081234567890",
        "persetujuan": "on",
        "situs_web": "",
        "token": token_lama(),
        "foto": file_foto(),
    }
    data.update(ubah)
    return {k: v for k, v in data.items() if v is not None}
