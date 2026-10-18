"""Unduhan Excel biodata (versi umum disamarkan dan versi lengkap) dan ZIP foto per kontingen."""

from __future__ import annotations

import io
import re
import zipfile
from datetime import datetime, time

import xlsxwriter
from django.utils import timezone

from apps.inti.models import Tingkat
from apps.inti.utils import tanggal_id

from . import foto as foto_mod
from . import nik as nik_mod
from .kueri import tabel_kontingen
from .models import Peserta
from .services import tanggal_acuan_usia, usia_pada

KOLOM_UMUM = [
    ("Kode pendaftaran", 16), ("Nama lengkap", 30), ("Kode kontingen", 10), ("Kontingen", 34),
    ("Tingkat", 9), ("Peran", 20), ("Jenis kelamin", 12), ("Tempat lahir", 16), ("Tanggal lahir", 13),
    ("Umur per 12 Nov 2026", 10), ("NIK (disamarkan)", 19), ("No. induk anggota", 16), ("Gol. darah", 9),
    ("Telepon", 16), ("Foto", 6), ("Tanda", 40), ("Masuk pada", 18), ("Sumber", 12),
]  # fmt: skip
KOLOM_LENGKAP_TAMBAHAN = [("NIK", 19), ("Alamat", 45), ("Nama orang tua/wali", 26), ("Telepon orang tua/wali", 18)]


def _baris(p: Peserta, acuan, lengkap: bool) -> list:
    tanda = "; ".join(t.get_jenis_display() for t in p.penanda.all() if t.diabaikan_pada is None)
    baris = [
        p.kode_pendaftaran, p.nama_lengkap, p.kontingen.kode, p.kontingen.nama, p.get_tingkat_display(),
        p.get_peran_display(), p.get_jenis_kelamin_display(), p.tempat_lahir, p.tanggal_lahir,
        usia_pada(p.tanggal_lahir, acuan), p.nik_samar, p.nomor_induk_anggota, p.get_golongan_darah_display(),
        p.telepon, "ada" if p.foto_path else "tidak", tanda, timezone.localtime(p.dibuat_pada).replace(tzinfo=None),
        p.get_sumber_display(),
    ]  # fmt: skip
    if lengkap:
        baris += [nik_mod.dekripsi(p.nik_terenkripsi), p.alamat, p.nama_orang_tua, p.telepon_orang_tua]
    return baris


def excel_biodata(qs, lengkap: bool, keterangan_saringan: str = "") -> bytes:
    """Satu sheet gabungan + satu sheet per tingkat + ringkasan kontingen."""
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True, "remove_timezone": True})
    f_judul = wb.add_format({"bold": True, "font_size": 13, "font_color": "#E2451F"})
    f_kepala = wb.add_format(
        {
            "bold": True,
            "bg_color": "#FFF3E4",
            "border": 1,
            "border_color": "#F5D2B3",
            "text_wrap": True,
            "valign": "top",
        }
    )
    f_tgl = wb.add_format({"num_format": "dd/mm/yyyy"})
    f_waktu = wb.add_format({"num_format": "dd/mm/yyyy hh:mm"})
    f_teks = wb.add_format({"num_format": "@"})
    kolom = KOLOM_UMUM + (KOLOM_LENGKAP_TAMBAHAN if lengkap else [])
    acuan = tanggal_acuan_usia()
    data = list(qs.prefetch_related("penanda"))
    versi = "LENGKAP (RAHASIA)" if lengkap else "umum (NIK disamarkan)"

    def tulis_sheet(nama: str, isi: list[Peserta]):
        ws = wb.add_worksheet(nama)
        ws.write(0, 0, f"Biodata Jumbara PMR Kab. Bulungan V 2026 - versi {versi}", f_judul)
        ws.write(1, 0, f"Diunduh {tanggal_id(timezone.now())} {timezone.localtime():%H.%M} WITA. {keterangan_saringan}")
        for i, (judul, lebar) in enumerate(kolom):
            ws.write(3, i, judul, f_kepala)
            ws.set_column(i, i, lebar)
        for r, p in enumerate(isi, start=4):
            for c, nilai in enumerate(_baris(p, acuan, lengkap)):
                judul = kolom[c][0]
                if judul == "Tanggal lahir":
                    ws.write_datetime(r, c, datetime.combine(nilai, time()), f_tgl)
                elif judul == "Masuk pada":
                    ws.write_datetime(r, c, nilai, f_waktu)
                elif judul in ("NIK", "Telepon", "Telepon orang tua/wali", "No. induk anggota"):
                    ws.write_string(r, c, nilai or "", f_teks)
                else:
                    ws.write(r, c, nilai)
        ws.freeze_panes(4, 2)
        if isi:
            ws.autofilter(3, 0, 3 + len(isi), len(kolom) - 1)

    tulis_sheet("Semua", data)
    for t in Tingkat:
        tulis_sheet(t.label, [p for p in data if p.tingkat == t.value])

    ws = wb.add_worksheet("Kontingen")
    kepala = ["Kode", "Kontingen", "Tingkat", "Kuota", "Terisi", "Sisa/lebih", "Peserta", "Pimpinan",
              "Pembina pendamping", "Peninjau", "Orang bertanda"]  # fmt: skip
    for i, judul in enumerate(kepala):
        ws.write(0, i, judul, f_kepala)
    ws.set_column(0, 0, 8)
    ws.set_column(1, 1, 36)
    ws.set_column(2, 10, 11)
    for r, b in enumerate(tabel_kontingen(), start=1):
        k = b["k"]
        ws.write_row(r, 0, [k.kode, k.nama, k.get_tingkat_display(), k.kuota, k.terisi, b["sisa"], k.n_peserta,
                            k.n_pimpinan, k.n_pembina, k.n_peninjau, b["bertanda"]])  # fmt: skip
    wb.close()
    return buf.getvalue()


def _nama_file_aman(teks: str) -> str:
    teks = re.sub(r"[^\w\s.\-]", "", teks, flags=re.UNICODE).strip()
    return re.sub(r"\s+", " ", teks)[:80] or "tanpa-nama"


def zip_foto(qs) -> tuple[bytes, int]:
    """ZIP berisi foto (nama file = nama orang + kode pendaftaran). Mengembalikan (isi, jumlah)."""
    buf = io.BytesIO()
    jumlah = 0
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as z:
        for p in qs:
            path = foto_mod.path_lengkap(p.foto_path)
            if path is None:
                continue
            z.write(path, f"{_nama_file_aman(p.nama_lengkap)} - {p.kode_pendaftaran}.jpg")
            jumlah += 1
    return buf.getvalue(), jumlah
