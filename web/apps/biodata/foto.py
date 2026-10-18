"""Pemrosesan foto 3x4 dengan Pillow dan penyimpanan di folder privat.

Server tidak mempercayai browser: tipe file diperiksa dari isi, orientasi EXIF diluruskan,
dipotong 3:4, diubah ke 600x800, disimpan JPEG tanpa metadata (EXIF/GPS terhapus).
"""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageOps, UnidentifiedImageError

UKURAN_MAKS = 5 * 1024 * 1024
LEBAR, TINGGI = 600, 800
FORMAT_BOLEH = {"JPEG", "PNG", "MPO"}  # MPO = JPEG dari sebagian kamera HP
# Cegah "bom gambar" (gambar kecil berukuran piksel raksasa).
Image.MAX_IMAGE_PIXELS = 60_000_000


class FotoTidakValid(ValueError):
    pass


@dataclass
class HasilFoto:
    isi_jpeg: bytes
    hash_asli: str


def baca_potongan(teks: str) -> dict | None:
    """Koordinat potong dari browser: {"x","y","w","h","r"} dalam piksel gambar yang diunggah."""
    if not teks:
        return None
    try:
        data = json.loads(teks)
        hasil = {k: float(data[k]) for k in ("x", "y", "w", "h")}
        hasil["r"] = int(float(data.get("r", 0))) % 360
    except (ValueError, KeyError, TypeError):
        return None
    if hasil["w"] <= 0 or hasil["h"] <= 0:
        return None
    return hasil


def _potong_tengah(img: Image.Image) -> Image.Image:
    lebar, tinggi = img.size
    if lebar / tinggi > 3 / 4:
        baru = round(tinggi * 3 / 4)
        kiri = (lebar - baru) // 2
        return img.crop((kiri, 0, kiri + baru, tinggi))
    baru = round(lebar * 4 / 3)
    atas = (tinggi - baru) // 2
    return img.crop((0, atas, lebar, atas + baru))


def proses(berkas, potongan: dict | None = None) -> HasilFoto:
    """Validasi dan olah file unggahan menjadi JPEG 600x800. Melempar FotoTidakValid."""
    if berkas.size > UKURAN_MAKS:
        raise FotoTidakValid("Ukuran foto lebih dari 5 MB. Pilih foto yang lebih kecil.")
    isi = berkas.read()
    if len(isi) > UKURAN_MAKS:
        raise FotoTidakValid("Ukuran foto lebih dari 5 MB. Pilih foto yang lebih kecil.")
    hash_asli = hashlib.sha256(isi).hexdigest()
    try:
        with Image.open(io.BytesIO(isi)) as cek:
            if cek.format not in FORMAT_BOLEH:
                raise FotoTidakValid("Foto harus berformat JPG atau PNG.")
            cek.verify()
        img = Image.open(io.BytesIO(isi))
        img.load()
    except FotoTidakValid:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError, ValueError):
        raise FotoTidakValid("File ini bukan foto JPG atau PNG yang bisa dibaca.") from None

    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        latar = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            latar.paste(img, mask=img.split()[-1])
        else:
            latar.paste(img.convert("RGB"))
        img = latar
    else:
        img = img.convert("RGB")

    if potongan:
        if potongan.get("r"):
            # Cropper.js memutar searah jarum jam; Pillow berlawanan arah.
            img = img.rotate(-potongan["r"], expand=True)
        lebar, tinggi = img.size
        x = max(0, min(potongan["x"], lebar - 1))
        y = max(0, min(potongan["y"], tinggi - 1))
        w = max(1, min(potongan["w"], lebar - x))
        h = max(1, min(potongan["h"], tinggi - y))
        img = img.crop((round(x), round(y), round(x + w), round(y + h)))
    # Pastikan tepat 3:4 walau koordinat dari browser sedikit meleset.
    img = _potong_tengah(img)
    img = img.resize((LEBAR, TINGGI), Image.Resampling.LANCZOS)

    keluaran = io.BytesIO()
    img.save(keluaran, format="JPEG", quality=85, optimize=True)  # tanpa exif=
    return HasilFoto(isi_jpeg=keluaran.getvalue(), hash_asli=hash_asli)


def folder_foto() -> Path:
    return Path(settings.SIGAP_FOLDER_PRIVAT) / "foto"


def simpan(kode_pendaftaran: str, isi_jpeg: bytes, tahun: int) -> str:
    """Simpan ke folder privat. Mengembalikan path relatif terhadap folder privat."""
    relatif = Path("foto") / str(tahun) / f"{kode_pendaftaran}.jpg"
    tujuan = Path(settings.SIGAP_FOLDER_PRIVAT) / relatif
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    sementara = tujuan.with_suffix(".tmp")
    sementara.write_bytes(isi_jpeg)
    sementara.replace(tujuan)
    return relatif.as_posix()


def path_lengkap(relatif: str) -> Path | None:
    """Path absolut foto, hanya jika berada di dalam folder privat (cegah path traversal)."""
    if not relatif:
        return None
    dasar = Path(settings.SIGAP_FOLDER_PRIVAT).resolve()
    path = (dasar / relatif).resolve()
    if dasar not in path.parents:
        return None
    return path if path.is_file() else None


def hapus(relatif: str) -> None:
    path = path_lengkap(relatif)
    if path:
        path.unlink(missing_ok=True)
