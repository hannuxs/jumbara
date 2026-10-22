"""PDF kartu peserta B-2 (4 per F4, garis potong) dan lembar QR kontingen F4 (ReportLab).

Semua ukuran dalam milimeter. QR digambar sebagai vektor (kotak-kotak) agar tajam saat dicetak.
Kartu hanya memuat foto, nama, peran, kontingen, tingkat, QR, dan kode kartu (tanpa data pribadi lain).
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass
from pathlib import Path

import segno
from django.conf import settings
from django.utils import timezone
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from apps.biodata import foto as foto_mod
from apps.biodata.models import Peserta
from apps.inti import pengaturan
from apps.inti.utils import tanggal_id
from apps.kontingen.models import Kontingen

from . import token as tk
from .services import urutkan_untuk_cetak

F4 = (215 * mm, 330 * mm)
FOLDER_IMG = Path(settings.BASE_DIR) / "static" / "img"
NAVY = colors.HexColor("#1F2937")
ABU = colors.HexColor("#6B7280")
GARIS = colors.HexColor("#D1D5DB")
ORANYE = colors.HexColor("#F26B1D")
WARNA_TINGKAT = {
    "MULA": (colors.HexColor("#16A34A"), colors.white),
    "MADYA": (colors.HexColor("#2563EB"), colors.white),
    "WIRA": (colors.HexColor("#EAB308"), NAVY),
}
CATATAN_CETAK = "Cetak dengan skala 100% (Actual size), kertas F4 215 x 330 mm."


@dataclass
class UkuranKartu:
    lebar: float
    tinggi: float


def ukuran_kartu() -> UkuranKartu:
    """Ukuran kartu dari pengaturan (bawaan B-2 88 x 125 mm)."""
    nilai = pengaturan.semua()
    try:
        lebar = float(nilai.get("kartu.lebar_mm") or 88)
        tinggi = float(nilai.get("kartu.tinggi_mm") or 125)
    except (TypeError, ValueError):
        lebar, tinggi = 88, 125
    return UkuranKartu(lebar * mm, tinggi * mm)


# --- Gambar dasar --------------------------------------------------------------


def _logo(c: canvas.Canvas, nama: str, x: float, y: float, tinggi: float, kanan: bool = False) -> float:
    img = ImageReader(str(FOLDER_IMG / nama))
    lb, tg = img.getSize()
    lebar = tinggi * lb / tg
    c.drawImage(img, x - lebar if kanan else x, y, width=lebar, height=tinggi, mask="auto")
    return lebar


def gambar_qr(c: canvas.Canvas, isi: str, x: float, y: float, ukuran: float, tepi_modul: int = 2) -> None:
    """QR vektor di kotak (x, y, ukuran) termasuk tepi putih `tepi_modul` modul. Koreksi galat Q."""
    qr = segno.make(isi, error="q", micro=False, boost_error=False)
    matriks = qr.matrix
    n = len(matriks)
    modul = ukuran / (n + 2 * tepi_modul)
    c.saveState()
    c.setFillColor(colors.white)
    c.rect(x, y, ukuran, ukuran, stroke=0, fill=1)
    c.setFillColor(colors.black)
    for baris, isi_baris in enumerate(matriks):
        kolom = 0
        while kolom < n:
            if isi_baris[kolom]:
                awal = kolom
                while kolom < n and isi_baris[kolom]:
                    kolom += 1
                # Satu persegi panjang per deret modul hitam (PDF lebih kecil), sedikit ditumpuk agar tanpa celah.
                c.rect(
                    x + (tepi_modul + awal) * modul,
                    y + ukuran - (tepi_modul + baris + 1) * modul,
                    (kolom - awal) * modul,
                    modul * 1.02,
                    stroke=0,
                    fill=1,
                )
            else:
                kolom += 1
    c.restoreState()


def _foto(peserta: Peserta) -> ImageReader | None:
    """Foto 3:4 dari folder privat, diperkecil ke 300x400 px (cukup tajam untuk 24 x 32 mm)."""
    path = foto_mod.path_lengkap(peserta.foto_path)
    if path is None:
        return None
    with Image.open(path) as img:
        kecil = img.convert("RGB").resize((300, 400), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    kecil.save(buf, format="JPEG", quality=88)
    buf.seek(0)
    return ImageReader(buf)


def _pas_baris(
    teks: str, font: str, lebar: float, besar: float, kecil: float, maks_baris: int
) -> tuple[float, list[str]]:
    """Ukuran huruf terbesar agar teks muat maksimal `maks_baris` baris."""
    ukuran = besar
    while ukuran >= kecil:
        baris = simpleSplit(teks, font, ukuran, lebar)
        if len(baris) <= maks_baris:
            return ukuran, baris
        ukuran -= 0.5
    return kecil, simpleSplit(teks, font, kecil, lebar)[: maks_baris + 1]


def _teks_tengah_muat(c, teks, font, besar, kecil, x_tengah, y, lebar):
    ukuran = besar
    while ukuran > kecil and stringWidth(teks, font, ukuran) > lebar:
        ukuran -= 0.25
    c.setFont(font, ukuran)
    c.drawCentredString(x_tengah, y, teks)


# --- Kartu -----------------------------------------------------------------------


def gambar_kartu(c: canvas.Canvas, p: Peserta, x: float, y: float, uk: UkuranKartu) -> None:
    """Satu kartu dengan sudut kiri bawah di (x, y)."""
    w, h = uk.lebar, uk.tinggi
    tepi = 3.5 * mm
    atas = y + h
    warna, warna_teks = WARNA_TINGKAT.get(p.tingkat, (ORANYE, colors.white))

    # Bingkai kartu.
    c.setStrokeColor(GARIS)
    c.setLineWidth(0.5)
    c.roundRect(x, y, w, h, 3 * mm, stroke=1, fill=0)

    # 1. Kepala putih: logo PMI kiri, logo Jumbara V kanan, judul di tengah.
    tinggi_logo = 12 * mm
    y_logo = atas - 3 * mm - tinggi_logo
    lebar_pmi = _logo(c, "pmi-logo-160.png", x + tepi, y_logo, tinggi_logo)
    lebar_jv = _logo(c, "jumbara-v-400.jpg", x + w - tepi, y_logo, tinggi_logo, kanan=True)
    x_tengah = x + tepi + lebar_pmi + (w - 2 * tepi - lebar_pmi - lebar_jv) / 2
    lebar_judul = w - 2 * tepi - lebar_pmi - lebar_jv - 2 * mm
    c.setFillColor(NAVY)
    _teks_tengah_muat(c, "JUMBARA PMR TINGKAT", "Helvetica-Bold", 6.6, 4.5, x_tengah, atas - 7 * mm, lebar_judul)
    _teks_tengah_muat(c, "KABUPATEN BULUNGAN V", "Helvetica-Bold", 6.6, 4.5, x_tengah, atas - 9.8 * mm, lebar_judul)
    _teks_tengah_muat(c, "TAHUN 2026", "Helvetica-Bold", 6.6, 4.5, x_tengah, atas - 12.6 * mm, lebar_judul)
    c.setFillColor(ABU)
    _teks_tengah_muat(
        c, "Unggul - Responsif - Berkarakter", "Helvetica-Oblique", 4.8, 3.5, x_tengah, atas - 15 * mm, lebar_judul
    )

    # 2. Pita warna tingkat bertuliskan PERAN.
    y_pita = atas - 18 * mm - 6.5 * mm
    c.setFillColor(warna)
    c.rect(x + 0.25 * mm, y_pita, w - 0.5 * mm, 6.5 * mm, stroke=0, fill=1)
    c.setFillColor(warna_teks)
    _teks_tengah_muat(
        c, p.get_peran_display().upper(), "Helvetica-Bold", 10, 6, x + w / 2, y_pita + 2.1 * mm, w - 2 * tepi
    )

    # 3. Foto 3x4 (24 x 32 mm) dan identitas di sebelahnya.
    tinggi_foto, lebar_foto = 32 * mm, 24 * mm
    y_foto = y_pita - 2.5 * mm - tinggi_foto
    foto = _foto(p)
    if foto is not None:
        c.drawImage(foto, x + tepi, y_foto, width=lebar_foto, height=tinggi_foto)
    else:
        c.setFillColor(colors.HexColor("#F3F4F6"))
        c.rect(x + tepi, y_foto, lebar_foto, tinggi_foto, stroke=0, fill=1)
        c.setFillColor(ABU)
        c.setFont("Helvetica", 7)
        c.drawCentredString(x + tepi + lebar_foto / 2, y_foto + tinggi_foto / 2, "FOTO 3x4")
    c.setStrokeColor(NAVY)
    c.setLineWidth(0.4)
    c.rect(x + tepi, y_foto, lebar_foto, tinggi_foto, stroke=1, fill=0)

    x_id = x + tepi + lebar_foto + 3 * mm
    lebar_id = x + w - tepi - x_id
    yy = y_pita - 2.5 * mm
    ukuran, baris = _pas_baris(p.nama_lengkap.upper(), "Helvetica-Bold", lebar_id, 12, 7, 2)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", ukuran)
    for b in baris:
        yy -= ukuran * 1.08
        c.drawString(x_id, yy, b)
    yy -= 2.2 * mm
    ukuran_k, baris_k = _pas_baris(p.kontingen.nama, "Helvetica", lebar_id, 7.5, 5.5, 3)
    c.setFillColor(colors.HexColor("#374151"))
    c.setFont("Helvetica", ukuran_k)
    for b in baris_k:
        yy -= ukuran_k * 1.15
        c.drawString(x_id, yy, b)
    # Lencana tingkat (tetap terbaca bila dicetak hitam putih karena bertuliskan TINGKAT ...).
    teks_t = f"TINGKAT {p.get_tingkat_display().upper()}"
    lebar_t = stringWidth(teks_t, "Helvetica-Bold", 7) + 3 * mm
    y_t = max(y_foto, yy - 6 * mm)
    c.setFillColor(warna)
    c.roundRect(x_id, y_t, lebar_t, 4.4 * mm, 1.2 * mm, stroke=0, fill=1)
    c.setFillColor(warna_teks)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(x_id + 1.5 * mm, y_t + 1.35 * mm, teks_t)

    # 4. QR besar + kode kartu + kaki.
    y_kaki = y + 3 * mm
    y_kode = y_kaki + 4.2 * mm
    ruang = (y_foto - 2 * mm) - (y_kode + 4.5 * mm)
    ukuran_qr = min(ruang, w - 2 * tepi, 52 * mm)
    y_qr = y_kode + 4.5 * mm + (ruang - ukuran_qr) / 2
    gambar_qr(c, tk.isi_qr_peserta(p.qr_token), x + (w - ukuran_qr) / 2, y_qr, ukuran_qr)
    c.setFillColor(NAVY)
    c.setFont("Courier-Bold", 12)
    c.drawCentredString(x + w / 2, y_kode, p.kode_kartu or "")
    c.setFillColor(ABU)
    c.setFont("Helvetica", 5.5)
    c.drawString(x + tepi, y_kaki, "Kartu wajib dipakai selama kegiatan")
    c.drawRightString(x + w - tepi, y_kaki, f"{p.kontingen.kode} · v{p.versi_kartu}")


# --- Lembar F4 (4 kartu) ------------------------------------------------------------


def posisi_kartu(uk: UkuranKartu) -> list[tuple[float, float]]:
    """Sudut kiri bawah 4 kartu di F4: urutan kiri atas, kanan atas, kiri bawah, kanan bawah."""
    jarak = 8 * mm
    kiri = (F4[0] - 2 * uk.lebar - jarak) / 2
    bawah = (F4[1] - 2 * uk.tinggi - jarak) / 2
    xs = [kiri, kiri + uk.lebar + jarak]
    ys = [bawah + uk.tinggi + jarak, bawah]
    return [(xs[0], ys[0]), (xs[1], ys[0]), (xs[0], ys[1]), (xs[1], ys[1])]


def _garis_potong(c: canvas.Canvas, uk: UkuranKartu) -> None:
    pos = posisi_kartu(uk)
    c.saveState()
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.3)
    jarak, panjang = 1 * mm, 3 * mm
    for x, y in pos:
        for sx, sy in ((x, y), (x + uk.lebar, y), (x, y + uk.tinggi), (x + uk.lebar, y + uk.tinggi)):
            arah_x = -1 if sx == x else 1
            arah_y = -1 if sy == y else 1
            c.line(sx + arah_x * jarak, sy, sx + arah_x * (jarak + panjang), sy)
            c.line(sx, sy + arah_y * jarak, sx, sy + arah_y * (jarak + panjang))
    # Garis putus-putus tipis di tengah celah antar kartu.
    c.setStrokeColor(colors.HexColor("#9CA3AF"))
    c.setDash(2, 2)
    x_tengah = pos[0][0] + uk.lebar + 4 * mm
    y_tengah = pos[2][1] + uk.tinggi + 4 * mm
    c.line(x_tengah, pos[2][1], x_tengah, pos[0][1] + uk.tinggi)
    c.line(pos[0][0], y_tengah, pos[1][0] + uk.lebar, y_tengah)
    c.restoreState()


def _kaki_lembar(c: canvas.Canvas, teks: str) -> None:
    c.setFillColor(ABU)
    c.setFont("Helvetica", 7)
    c.drawCentredString(F4[0] / 2, 8 * mm, teks)


def _kepala_halaman(c: canvas.Canvas, y_atas: float, tinggi_logo: float) -> float:
    """Logo PMI kiri dan Jumbara V kanan di bagian atas halaman F4. Mengembalikan y bawah kepala."""
    y_logo = y_atas - tinggi_logo
    _logo(c, "pmi-logo-160.png", 15 * mm, y_logo, tinggi_logo)
    _logo(c, "jumbara-v-400.jpg", F4[0] - 15 * mm, y_logo, tinggi_logo, kanan=True)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(F4[0] / 2, y_atas - tinggi_logo * 0.38, "JUMBARA PMR TINGKAT KABUPATEN BULUNGAN V 2026")
    c.setFillColor(ABU)
    c.setFont("Helvetica-Oblique", 8.5)
    c.drawCentredString(F4[0] / 2, y_atas - tinggi_logo * 0.38 - 5 * mm, "Unggul - Responsif - Berkarakter")
    return y_logo


def _sampul(c: canvas.Canvas, k: Kontingen, daftar: list[Peserta], judul: str) -> None:
    """Halaman pertama: daftar isi untuk pembagian kartu saat daftar ulang."""
    y = _kepala_halaman(c, F4[1] - 15 * mm, 18 * mm) - 10 * mm
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(15 * mm, y, judul)
    y -= 7 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(15 * mm, y, f"{k.kode}  {k.nama}  (Tingkat {k.get_tingkat_display()})")
    y -= 6 * mm
    hitung: dict[str, int] = {}
    for p in daftar:
        hitung[p.get_peran_display()] = hitung.get(p.get_peran_display(), 0) + 1
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#374151"))
    ringkas = ", ".join(f"{n} {peran}" for peran, n in hitung.items())
    c.drawString(15 * mm, y, f"Jumlah kartu: {len(daftar)} ({ringkas})")
    y -= 5 * mm
    c.drawString(
        15 * mm, y, f"Dibuat {tanggal_id(timezone.now())} pukul {timezone.localtime():%H.%M} WITA. {CATATAN_CETAK}"
    )
    y -= 8 * mm

    kolom = [
        ("No", 10 * mm),
        ("Nama", 78 * mm),
        ("Peran", 38 * mm),
        ("Kode kartu", 24 * mm),
        ("Lembar", 20 * mm),
        ("Cek", 15 * mm),
    ]
    tinggi_baris = 5.2 * mm

    def kepala_tabel(yk: float) -> float:
        c.setFillColor(colors.HexColor("#FFF3E4"))
        c.rect(15 * mm, yk - 1.6 * mm, F4[0] - 30 * mm, tinggi_baris, stroke=0, fill=1)
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 8.5)
        xx = 16 * mm
        for nama, lebar in kolom:
            c.drawString(xx, yk, nama)
            xx += lebar
        return yk - tinggi_baris

    y = kepala_tabel(y)
    for i, p in enumerate(daftar):
        if y < 18 * mm:
            _kaki_lembar(c, f"{judul} · {k.kode} {k.nama} · daftar isi (lanjutan di halaman berikut)")
            c.showPage()
            y = kepala_tabel(F4[1] - 20 * mm)
        lembar, posisi = divmod(i, 4)
        nilai = [
            str(i + 1),
            p.nama_lengkap,
            p.get_peran_display(),
            p.kode_kartu or "",
            f"{lembar + 1}-{posisi + 1}",
            "[   ]",
        ]
        c.setFillColor(NAVY)
        c.setFont("Helvetica", 8.5)
        xx = 16 * mm
        for (_, lebar), teks in zip(kolom, nilai, strict=True):
            # Huruf mengecil agar nama panjang tetap utuh dalam satu baris.
            ukuran = 8.5
            while ukuran > 5.5 and stringWidth(teks, "Helvetica", ukuran) > lebar - 2 * mm:
                ukuran -= 0.25
            c.setFont("Helvetica", ukuran)
            c.drawString(xx, y, teks)
            xx += lebar
        c.setStrokeColor(colors.HexColor("#F3F4F6"))
        c.setLineWidth(0.3)
        c.line(15 * mm, y - 1.6 * mm, F4[0] - 15 * mm, y - 1.6 * mm)
        y -= tinggi_baris
    c.setFillColor(ABU)
    c.setFont("Helvetica", 7.5)
    c.drawString(
        15 * mm,
        max(y - 4 * mm, 14 * mm),
        "Lembar 1-2 = lembar kartu ke-1, posisi ke-2 (posisi 1 kiri atas, 2 kanan atas, 3 kiri bawah, 4 kanan bawah).",
    )
    _kaki_lembar(c, f"{judul} · {k.kode} {k.nama} · daftar isi")
    c.showPage()


def kartu_pdf(peserta: list[Peserta], judul: str, kontingen: Kontingen | None = None) -> bytes:
    """PDF F4 berisi kartu (4 per lembar). Bila `kontingen` diisi, halaman pertama berupa sampul."""
    uk = ukuran_kartu()
    daftar = urutkan_untuk_cetak(peserta)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=F4)
    c.setTitle(judul)
    c.setAuthor("SIGAP JUMBARA")
    if kontingen is not None and daftar:
        _sampul(c, kontingen, daftar, judul)
    jumlah_lembar = max(1, math.ceil(len(daftar) / 4))
    pos = posisi_kartu(uk)
    for lembar in range(jumlah_lembar):
        bagian = daftar[lembar * 4 : lembar * 4 + 4]
        _garis_potong(c, uk)
        for (x, y), p in zip(pos, bagian, strict=False):
            gambar_kartu(c, p, x, y, uk)
        _kaki_lembar(c, f"{CATATAN_CETAK}  {judul} · lembar {lembar + 1}/{jumlah_lembar}")
        c.showPage()
    c.save()
    return buf.getvalue()


# --- Lembar QR kontingen F4 ----------------------------------------------------------


def qr_kontingen_pdf(daftar: list[Kontingen]) -> bytes:
    """Satu lembar F4 per kontingen untuk ditempel di tenda (Anjangsana)."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=F4)
    c.setTitle("QR Kontingen Jumbara V 2026")
    c.setAuthor("SIGAP JUMBARA")
    url_anjangsana = f"{settings.SIGAP_URL}/anjangsana/"
    for k in daftar:
        warna, warna_teks = WARNA_TINGKAT.get(k.tingkat, (ORANYE, colors.white))
        y = _kepala_halaman(c, F4[1] - 14 * mm, 24 * mm) - 9 * mm
        c.setFillColor(ABU)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(F4[0] / 2, y, "KONTINGEN")
        ukuran, baris = _pas_baris(k.nama.upper(), "Helvetica-Bold", F4[0] - 30 * mm, 30, 16, 2)
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", ukuran)
        for b in baris:
            y -= ukuran * 1.1
            c.drawCentredString(F4[0] / 2, y, b)
        # Pita tingkat di bawah nama (jarak cukup agar tidak menimpa huruf).
        y -= 14 * mm
        c.setFillColor(warna)
        c.roundRect(15 * mm, y - 3 * mm, F4[0] - 30 * mm, 11 * mm, 3 * mm, stroke=0, fill=1)
        c.setFillColor(warna_teks)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(F4[0] / 2, y + 0.5 * mm, f"TINGKAT {k.get_tingkat_display().upper()}  ·  {k.kode}")
        ukuran_qr = 150 * mm
        y_qr = y - 7 * mm - ukuran_qr
        gambar_qr(c, tk.isi_qr_kontingen(k.qr_token), (F4[0] - ukuran_qr) / 2, y_qr, ukuran_qr, tepi_modul=3)
        y = y_qr - 9 * mm
        c.setFillColor(ORANYE)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(F4[0] / 2, y, "ANJANGSANA")
        y -= 7 * mm
        c.setFillColor(NAVY)
        c.setFont("Helvetica", 12)
        for b in simpleSplit(
            "Tamu, pindai QR ini lewat link Anjangsana untuk mengisi buku tamu dan review.",
            "Helvetica",
            12,
            F4[0] - 40 * mm,
        ):
            c.drawCentredString(F4[0] / 2, y, b)
            y -= 5.5 * mm
        c.setFont("Courier-Bold", 13)
        c.drawCentredString(F4[0] / 2, y - 1 * mm, url_anjangsana)
        _kaki_lembar(c, f"{CATATAN_CETAK} Tempel di tenda kontingen. QR tidak berlaku bila diganti superadmin.")
        c.showPage()
    if not daftar:
        c.showPage()
    c.save()
    return buf.getvalue()
