"""Cadangan database (mysqldump/mariadb-dump) + folder foto dalam satu ZIP.

Dipanggil dari tombol superadmin dan dari `sigap_jadwal` (Windows Task Scheduler).
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("sigap")
AWALAN = "sigap_"


class GagalCadangan(RuntimeError):
    pass


@dataclass
class InfoCadangan:
    nama: str
    path: Path
    ukuran: int
    dibuat: datetime


def folder() -> Path:
    f = Path(settings.SIGAP_FOLDER_CADANGAN)
    f.mkdir(parents=True, exist_ok=True)
    return f


def daftar() -> list[InfoCadangan]:
    hasil = []
    for p in folder().glob(f"{AWALAN}*.zip"):
        st = p.stat()
        hasil.append(
            InfoCadangan(p.name, p, st.st_size, datetime.fromtimestamp(st.st_mtime, tz=timezone.get_current_timezone()))
        )
    return sorted(hasil, key=lambda x: x.dibuat, reverse=True)


def path_aman(nama: str) -> Path | None:
    """Path file cadangan berdasarkan nama, hanya jika ada di folder cadangan."""
    if "/" in nama or "\\" in nama or not nama.startswith(AWALAN) or not nama.endswith(".zip"):
        return None
    p = folder() / nama
    return p if p.is_file() else None


class _Kunci:
    """Kunci berkas sederhana agar dua proses tidak membuat cadangan bersamaan."""

    def __init__(self, path: Path, umur_maks: int = 3600):
        self.path = path
        self.umur_maks = umur_maks
        self.fd = None

    def __enter__(self):
        if self.path.exists() and time.time() - self.path.stat().st_mtime > self.umur_maks:
            self.path.unlink(missing_ok=True)
        try:
            self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise GagalCadangan("Cadangan lain sedang dibuat. Coba lagi beberapa menit lagi.") from None
        return self

    def __exit__(self, *exc):
        if self.fd is not None:
            os.close(self.fd)
        self.path.unlink(missing_ok=True)


def _dump_database(tujuan: Path) -> None:
    db = settings.DATABASES["default"]
    program = settings.SIGAP_MYSQLDUMP_PATH
    if not Path(program).is_file():
        raise GagalCadangan(f"Program mysqldump tidak ditemukan: {program}. Atur SIGAP_MYSQLDUMP_PATH di .env.")
    # Kata sandi lewat file opsi sementara agar tidak terlihat di daftar proses.
    with tempfile.NamedTemporaryFile("w", suffix=".cnf", delete=False, encoding="utf-8") as cnf:
        cnf.write("[client]\n")
        cnf.write(f"user={db['USER']}\n")
        cnf.write(f'password="{db["PASSWORD"]}"\n')
        cnf.write(f"host={db['HOST'] or '127.0.0.1'}\n")
        cnf.write(f"port={db['PORT'] or 3306}\n")
        path_cnf = cnf.name
    try:
        perintah = [
            program,
            f"--defaults-extra-file={path_cnf}",
            "--single-transaction",
            "--quick",
            "--routines",
            "--triggers",
            "--default-character-set=utf8mb4",
            "--hex-blob",
            f"--result-file={tujuan}",
            db["NAME"],
        ]
        bendera = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        hasil = subprocess.run(perintah, capture_output=True, text=True, timeout=1800, creationflags=bendera)
        if hasil.returncode != 0:
            raise GagalCadangan(f"mysqldump gagal: {hasil.stderr.strip()[:300]}")
    finally:
        Path(path_cnf).unlink(missing_ok=True)


def buat(alasan: str = "manual") -> InfoCadangan:
    """Buat satu ZIP: database.sql + foto/. Lalu hapus cadangan yang lebih lama dari batas hari."""
    f = folder()
    with _Kunci(f / ".cadangan.lock"):
        stempel = timezone.localtime().strftime("%Y%m%d_%H%M%S")
        nama = f"{AWALAN}{stempel}_{alasan}.zip"
        sementara = f / f".{nama}.tmp"
        with tempfile.TemporaryDirectory(prefix="sigap_cadangan_") as tmp:
            sql = Path(tmp) / "database.sql"
            _dump_database(sql)
            with zipfile.ZipFile(sementara, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
                z.write(sql, "database.sql")
                folder_foto = Path(settings.SIGAP_FOLDER_PRIVAT) / "foto"
                if folder_foto.is_dir():
                    for p in folder_foto.rglob("*.jpg"):
                        # Foto sudah JPEG terkompres; simpan tanpa kompresi ulang.
                        z.write(p, Path("foto") / p.relative_to(folder_foto), compress_type=zipfile.ZIP_STORED)
                z.writestr(
                    "BACA-SAYA.txt",
                    "Cadangan SIGAP JUMBARA\n"
                    f"Dibuat: {timezone.localtime():%Y-%m-%d %H:%M:%S} WITA ({alasan})\n"
                    "Isi: database.sql (impor ke MariaDB) dan folder foto/ (salin ke SIGAP_FOLDER_PRIVAT\\foto).\n"
                    "Panduan pemulihan: docs/21-DEPLOY-WINDOWS.md bagian 10.\n"
                    "PERHATIAN: berisi data pribadi anak. Simpan di tempat aman.\n",
                )
        tujuan = f / nama
        sementara.replace(tujuan)
        logger.info("Cadangan dibuat: %s", tujuan)
        hapus_lama()
        st = tujuan.stat()
        return InfoCadangan(nama, tujuan, st.st_size, timezone.localtime())


def hapus_lama() -> int:
    batas = time.time() - settings.SIGAP_CADANGAN_SIMPAN_HARI * 86400
    jumlah = 0
    for p in folder().glob(f"{AWALAN}*.zip"):
        if p.stat().st_mtime < batas:
            p.unlink(missing_ok=True)
            jumlah += 1
    return jumlah
