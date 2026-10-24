"""Pengisian data awal yang idempoten (aman dijalankan berulang). Dipakai `sigap_seed`."""

from __future__ import annotations

import csv
import secrets
import string
from datetime import date, time
from pathlib import Path

from django.conf import settings
from django.db import transaction

from apps.absensi.models import Kegiatan, KelompokKegiatan, TitikAbsen
from apps.akun.models import Pengguna, Peran
from apps.anjangsana.models import SesiAnjangsana
from apps.kontingen.models import Kontingen

from . import pengaturan
from .models import Pengaturan

FOLDER_DATA = Path(settings.BASE_DIR).parent / "data"

AKUN = [
    ("superadmin", Peran.SUPERADMIN, "SIGAP_SANDI_AWAL_SUPERADMIN"),
    ("panitia", Peran.PANITIA, "SIGAP_SANDI_AWAL_PANITIA"),
    ("juri", Peran.JURI, "SIGAP_SANDI_AWAL_JURI"),
]


def _baca_csv(nama: str, folder: Path) -> list[dict[str, str]]:
    with open(folder / nama, encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "").strip() for k, v in baris.items()} for baris in csv.DictReader(f)]


def _int(teks: str, bawaan: int | None = 0) -> int | None:
    try:
        return int(teks)
    except (TypeError, ValueError):
        return bawaan


def _jam(teks: str) -> time | None:
    if not teks:
        return None
    jam, menit = teks.split(":")[:2]
    return time(int(jam), int(menit))


def sandi_acak() -> str:
    huruf = string.ascii_letters + string.digits
    return "".join(secrets.choice(huruf) for _ in range(14))


def seed_akun(env, laporan: list[str]) -> None:
    for username, peran, kunci_env in AKUN:
        if Pengguna.objects.filter(peran=peran).exists():
            laporan.append(f"Akun {peran.label}: sudah ada (sandi tidak diubah)")
            continue
        sandi = env(kunci_env, default="") or ""
        acak = not sandi
        if acak:
            sandi = sandi_acak()
        user = Pengguna(username=username, peran=peran, wajib_ganti_sandi=True)
        if peran == Peran.SUPERADMIN:
            user.is_staff = True
            user.is_superuser = True
        user.set_password(sandi)
        user.save()
        if acak:
            laporan.append(f"Akun {username} dibuat. SANDI ACAK (catat sekarang, tidak ditampilkan lagi): {sandi}")
        else:
            laporan.append(f"Akun {username} dibuat dengan sandi dari {kunci_env} di .env")


def seed_kontingen(folder: Path, laporan: list[str]) -> None:
    baru = diperbarui = 0
    for b in _baca_csv("kontingen.csv", folder):
        kuota_awal = _int(b["kuota_awal"])
        data = {
            "nama": b["nama_resmi"],
            "tingkat": b["tingkat"],
            "nama_di_gform": b["nama_di_gform"],
            "pimpinan_gform": b["pimpinan_gform"][:255],
            "pendamping_gform": b["pendamping_gform"][:255],
            "jumlah_pendamping_tambahan": _int(b["jumlah_pendamping_tambahan"]),
            "peserta_inti_gform": _int(b["peserta_inti_gform"]),
            "peninjau_dihitung": _int(b["peninjau_dihitung"]),
            "catatan_data": b["catatan"],
        }
        k = Kontingen.semua.filter(kode=b["kode"]).first()
        if k is None:
            Kontingen.objects.create(kode=b["kode"], kuota_awal=kuota_awal, kuota=kuota_awal, **data)
            baru += 1
            continue
        # Data referensi GForm diperbarui; nama dan kuota yang sudah diubah superadmin dipertahankan.
        ubah = False
        for kolom in ("nama_di_gform", "pimpinan_gform", "pendamping_gform", "jumlah_pendamping_tambahan",
                      "peserta_inti_gform", "peninjau_dihitung", "catatan_data"):  # fmt: skip
            if getattr(k, kolom) != data[kolom]:
                setattr(k, kolom, data[kolom])
                ubah = True
        if k.kuota_awal != kuota_awal:
            k.kuota_awal = kuota_awal
            if not k.kuota_diubah_manual:
                k.kuota = kuota_awal
            ubah = True
        if ubah:
            k.save()
            diperbarui += 1
    laporan.append(f"Kontingen: {baru} baru, {diperbarui} diperbarui, total aktif {Kontingen.objects.count()}")


KEGIATAN_BUKAN_PILIHAN = ("daftar-ulang", "anjangsana")


def seed_kegiatan(folder: Path, laporan: list[str]) -> None:
    baru = 0
    for urutan, b in enumerate(_baca_csv("kegiatan.csv", folder), start=1):
        _, dibuat = Kegiatan.objects.get_or_create(
            kode=b["kode"],
            defaults={
                "nama": b["nama"],
                "kelompok": KelompokKegiatan[b["kelompok"].upper()],
                "dipisah_per_tingkat": b["dipisah_per_tingkat"].lower() == "ya",
                "kuota_default": _int(b["kuota_default_per_kontingen"], None),
                "rincian_kuota": b["rincian_kuota"][:255],
                "sistem_penilaian": b["sistem_penilaian"][:100],
                "catatan": b["catatan"],
                "urutan": urutan,
                # Daftar ulang dan Anjangsana diikuti semua orang, bukan pilihan di form biodata.
                "bisa_dipilih": b["kode"] not in KEGIATAN_BUKAN_PILIHAN,
            },
        )
        baru += dibuat
    laporan.append(f"Kegiatan: {baru} baru, total {Kegiatan.objects.count()}")


def seed_titik_absen(folder: Path, laporan: list[str]) -> None:
    kegiatan = {k.kode: k for k in Kegiatan.objects.all()}
    baru = 0
    for b in _baca_csv("titik_absen.csv", folder):
        keg = kegiatan.get(b["kegiatan_kode"])
        _, dibuat = TitikAbsen.objects.get_or_create(
            kode=b["kode"],
            defaults={
                "kegiatan": keg,
                "tingkat": b["tingkat"] or "SEMUA",
                "nama_tampil": b["nama_tampil"],
                "tanggal": date.fromisoformat(b["tanggal"]),
                "mulai": _jam(b["mulai"]),
                "selesai": _jam(b["selesai"]),
                "lokasi": b["lokasi"],
                "hitung_poin": b["kegiatan_kode"] != "daftar-ulang",
                "catatan": b["catatan"],
            },
        )
        baru += dibuat
    laporan.append(f"Titik absen: {baru} baru, total {TitikAbsen.objects.count()}")


def seed_sesi_anjangsana(folder: Path, laporan: list[str]) -> None:
    baru = 0
    for b in _baca_csv("sesi_anjangsana.csv", folder):
        _, dibuat = SesiAnjangsana.objects.get_or_create(
            tanggal=date.fromisoformat(b["tanggal"]),
            mulai=_jam(b["mulai"]),
            defaults={"selesai": _jam(b["selesai"])},
        )
        baru += dibuat
    laporan.append(f"Sesi Anjangsana: {baru} baru, total {SesiAnjangsana.objects.count()}")


def seed_pengaturan(laporan: list[str]) -> None:
    baru = 0
    for kunci, nilai in pengaturan.BAWAAN.items():
        _, dibuat = Pengaturan.objects.get_or_create(
            kunci=kunci, defaults={"nilai": nilai, "diubah_oleh": "sigap_seed"}
        )
        baru += dibuat
    laporan.append(f"Pengaturan: {baru} baru (yang sudah ada tidak diubah)")


def jalankan(env, folder: Path | None = None) -> list[str]:
    folder = folder or FOLDER_DATA
    laporan: list[str] = []
    with transaction.atomic():
        seed_akun(env, laporan)
        seed_kontingen(folder, laporan)
        seed_kegiatan(folder, laporan)
        seed_titik_absen(folder, laporan)
        seed_sesi_anjangsana(folder, laporan)
        seed_pengaturan(laporan)
    return laporan
