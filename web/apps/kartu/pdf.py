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
ORANYE_TUA = colors.HexColor("#E2451F")
# Latar kartu per tingkat (gradasi gelap -> terang) dan warna teks di atasnya; warna dasar = tema web.
GRADASI_TINGKAT = {
    "MULA": ([colors.HexColor("#14532D"), colors.HexColor("#15803D"), colors.HexColor("#16A34A")], colors.white),
    "MADYA": ([colors.HexColor("#1E3A8A"), colors.HexColor("#1D4ED8"), colors.HexColor("#2563EB")], colors.white),
    "WIRA": ([colors.HexColor("#FACC15"), colors.HexColor("#FDE047"), colors.HexColor("#FEF08A")], NAVY),
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


def _teks_kiri_muat(c, teks, font, besar, kecil, x, y, lebar):
    ukuran = besar
    while ukuran > kecil and stringWidth(teks, font, ukuran) > lebar:
        ukuran -= 0.25
    c.setFont(font, ukuran)
    c.drawString(x, y, teks)


def _teks_tengah_muat(c, teks, font, besar, kecil, x_tengah, y, lebar):
    ukuran = besar
    while ukuran > kecil and stringWidth(teks, font, ukuran) > lebar:
        ukuran -= 0.25
    c.setFont(font, ukuran)
    c.drawCentredString(x_tengah, y, teks)


# --- Kartu -----------------------------------------------------------------------


def _gradasi(tingkat: str) -> tuple[list, colors.Color]:
    """(warna gradasi gelap -> terang, warna teks di atasnya) per tingkat."""
    return GRADASI_TINGKAT.get(tingkat, ([ORANYE_TUA, ORANYE, colors.HexColor("#FB923C")], colors.white))


def _jalur_bulat(c: canvas.Canvas, x: float, y: float, w: float, h: float, r: float):
    p = c.beginPath()
    p.roundRect(x, y, w, h, r)
    return p


def _lencana(c: canvas.Canvas, teks: str, x: float, y: float, ukuran: float, isi, warna_teks, garis=None) -> float:
    """Lencana bulat (pil). Mengembalikan lebarnya."""
    lebar = stringWidth(teks, "Helvetica-Bold", ukuran) + 3.6 * mm
    tinggi = ukuran * 0.36 * mm + 2.6 * mm
    if isi is not None:
        c.setFillColor(isi)
    if garis is not None:
        c.setStrokeColor(garis)
        c.setLineWidth(0.6)
    c.roundRect(x, y, lebar, tinggi, tinggi / 2, stroke=1 if garis is not None else 0, fill=1 if isi is not None else 0)
    c.setFillColor(warna_teks)
    c.setFont("Helvetica-Bold", ukuran)
    c.drawString(x + 1.8 * mm, y + (tinggi - ukuran * 0.7) / 2 + 0.15 * mm, teks)
    return lebar


QR_KARTU = 45 * mm  # spesifikasi 13-KARTU-QR: QR minimal 45 x 45 mm


def gambar_kartu(c: canvas.Canvas, p: Peserta, x: float, y: float, uk: UkuranKartu) -> float:
    """Satu kartu (sudut kiri bawah di x, y). Mengembalikan ukuran QR (untuk tes).

    Desain (REVISI R7b): seluruh kartu berlatar gradasi warna tingkat; QR 45 mm dan kode kartu di pelat
    putih (tetap hitam putih); kapsul logo PMI + Jumbara V; foto berbingkai di kiri, di kanan lencana
    tingkat dan peran, nama, Nomor Induk Anggota, kontingen; pita teks di kaki."""
    w, h = uk.lebar, uk.tinggi
    tepi = 4.5 * mm
    atas = y + h

    def t(mm_dari_atas: float) -> float:
        return atas - mm_dari_atas * mm

    gradasi, teks = _gradasi(p.tingkat)
    # Warna teks lencana putih: warna tingkat tergelap; untuk Wira (kuning) pakai navy agar kontras.
    gelap = gradasi[0] if teks == colors.white else NAVY
    teks_lembut = colors.Color(teks.red, teks.green, teks.blue, alpha=0.85)
    radius = 3.5 * mm

    c.saveState()
    c.clipPath(_jalur_bulat(c, x, y, w, h, radius), stroke=0, fill=0)

    # 1. Latar penuh gradasi diagonal (gelap kiri atas -> terang kanan bawah) + hiasan transparan.
    c.linearGradient(x, atas, x + w, y, gradasi, extend=True)
    c.setFillColor(colors.white)
    c.setFillAlpha(0.10)
    c.circle(x + w + 2 * mm, atas - 8 * mm, 24 * mm, stroke=0, fill=1)
    c.circle(x - 6 * mm, y + 40 * mm, 20 * mm, stroke=0, fill=1)
    c.setFillAlpha(0.07)
    c.circle(x + w - 10 * mm, t(52), 9 * mm, stroke=0, fill=1)
    c.setFillAlpha(1)
    c.setStrokeColor(colors.white)
    c.setStrokeAlpha(0.18)
    c.setLineWidth(0.8)
    gel = c.beginPath()
    gel.moveTo(x, t(60))
    gel.curveTo(x + w * 0.35, t(54), x + w * 0.6, t(66), x + w, t(57))
    c.drawPath(gel, stroke=1, fill=0)
    c.setStrokeAlpha(1)

    # 2. Kapsul putih berisi logo PMI dan Jumbara V (logo PMI di latar terang, tidak diubah).
    tinggi_logo = 8 * mm
    img_pmi = ImageReader(str(FOLDER_IMG / "pmi-logo-160.png"))
    img_jv = ImageReader(str(FOLDER_IMG / "jumbara-v-400.jpg"))
    lb_pmi = tinggi_logo * img_pmi.getSize()[0] / img_pmi.getSize()[1]
    lb_jv = tinggi_logo * img_jv.getSize()[0] / img_jv.getSize()[1]
    jarak = 2.4 * mm
    lebar_kapsul = lb_pmi + lb_jv + jarak + 6 * mm
    tinggi_kapsul = tinggi_logo + 2.2 * mm
    xk = x + (w - lebar_kapsul) / 2
    yk = t(3) - tinggi_kapsul
    c.setFillColor(colors.white)
    c.roundRect(xk, yk, lebar_kapsul, tinggi_kapsul, tinggi_kapsul / 2, stroke=0, fill=1)
    c.drawImage(img_pmi, xk + 3 * mm, yk + 1.1 * mm, width=lb_pmi, height=tinggi_logo, mask="auto")
    c.setStrokeColor(GARIS)
    c.setLineWidth(0.4)
    x_sekat = xk + 3 * mm + lb_pmi + jarak / 2
    c.line(x_sekat, yk + 1.8 * mm, x_sekat, yk + tinggi_kapsul - 1.8 * mm)
    c.drawImage(img_jv, xk + 3 * mm + lb_pmi + jarak, yk + 1.1 * mm, width=lb_jv, height=tinggi_logo, mask="auto")

    # 3. Judul acara.
    c.setFillColor(teks)
    _teks_tengah_muat(c, "JUMBARA PMR KABUPATEN BULUNGAN V · 2026", "Helvetica-Bold", 6.6, 4.8, x + w / 2, t(16.6),
                      w - 2 * tepi)  # fmt: skip
    c.setFillColor(teks_lembut)
    _teks_tengah_muat(c, "Unggul · Responsif · Berkarakter", "Helvetica-Oblique", 4.8, 3.8, x + w / 2, t(19.1),
                      w - 2 * tepi)  # fmt: skip

    # 4. Foto 3x4 berbingkai putih dengan bayangan.
    lebar_foto, tinggi_foto = 24 * mm, 32 * mm
    xf = x + tepi + 0.6 * mm
    yf = t(23) - tinggi_foto
    bingkai = 1 * mm
    c.setFillColor(colors.black)
    c.setFillAlpha(0.18)
    c.roundRect(xf - bingkai + 0.6 * mm, yf - bingkai - 0.8 * mm, lebar_foto + 2 * bingkai, tinggi_foto + 2 * bingkai,
                2.2 * mm, stroke=0, fill=1)  # fmt: skip
    c.setFillAlpha(1)
    c.setFillColor(colors.white)
    c.roundRect(
        xf - bingkai, yf - bingkai, lebar_foto + 2 * bingkai, tinggi_foto + 2 * bingkai, 2.2 * mm, stroke=0, fill=1
    )
    foto = _foto(p)
    c.saveState()
    c.clipPath(_jalur_bulat(c, xf, yf, lebar_foto, tinggi_foto, 1.5 * mm), stroke=0, fill=0)
    if foto is not None:
        c.drawImage(foto, xf, yf, width=lebar_foto, height=tinggi_foto)
    else:
        c.setFillColor(colors.HexColor("#F3F4F6"))
        c.rect(xf, yf, lebar_foto, tinggi_foto, stroke=0, fill=1)
        c.setFillColor(ABU)
        c.setFont("Helvetica", 7)
        c.drawCentredString(xf + lebar_foto / 2, yf + tinggi_foto / 2, "FOTO 3x4")
    c.restoreState()

    # 5. Kolom identitas di kanan foto.
    x_id = xf + lebar_foto + bingkai + 3.5 * mm
    lebar_id = x + w - tepi - x_id
    # Lencana tingkat (isi putih, teks warna tingkat) dan peran (garis putih/gelap).
    y_lencana = t(23) - 4.4 * mm
    lb = _lencana(c, f"TINGKAT {p.get_tingkat_display().upper()}", x_id, y_lencana, 6.2, colors.white, gelap)
    peran = p.get_peran_display().upper()
    ukuran_peran = 6.2
    sisa = lebar_id - lb - 1.5 * mm
    if stringWidth(peran, "Helvetica-Bold", ukuran_peran) + 3.6 * mm <= sisa:
        _lencana(c, peran, x_id + lb + 1.5 * mm, y_lencana, ukuran_peran, None, teks, garis=teks)
        yy = y_lencana - 1.8 * mm
    else:
        while ukuran_peran > 4.6 and stringWidth(peran, "Helvetica-Bold", ukuran_peran) + 3.6 * mm > lebar_id:
            ukuran_peran -= 0.2
        y_peran = y_lencana - 5.2 * mm
        _lencana(c, peran, x_id, y_peran, ukuran_peran, None, teks, garis=teks)
        yy = y_peran - 1.8 * mm
    # Nama (maksimal 3 baris, huruf menyesuaikan).
    ukuran, baris = _pas_baris(p.nama_lengkap.upper(), "Helvetica-Bold", lebar_id, 11.5, 7, 3)
    c.setFillColor(teks)
    c.setFont("Helvetica-Bold", ukuran)
    for b in baris[:3]:
        yy -= ukuran * 1.08
        c.drawString(x_id, yy, b)
    nia = " ".join((p.nomor_induk_anggota or "").split())
    if nia:
        yy -= 3.2 * mm
        c.setFillColor(teks_lembut)
        _teks_kiri_muat(c, f"No. Induk Anggota: {nia}", "Helvetica", 6.6, 4.8, x_id, yy, lebar_id)
    # Garis pemisah tipis lalu kontingen.
    yy -= 2.2 * mm
    c.setStrokeColor(teks)
    c.setStrokeAlpha(0.45)
    c.setLineWidth(0.5)
    c.line(x_id, yy, x_id + min(lebar_id, 22 * mm), yy)
    c.setStrokeAlpha(1)
    ukuran_k, baris_k = _pas_baris(p.kontingen.nama, "Helvetica-Bold", lebar_id, 7, 5, 2)
    c.setFillColor(teks)
    c.setFont("Helvetica-Bold", ukuran_k)
    for b in baris_k[:2]:
        yy -= ukuran_k * 1.2
        c.drawString(x_id, yy, b)

    # 6. Pelat putih berisi QR 45 mm (hitam putih) dan kode kartu.
    pad = 3 * mm
    lebar_pelat = QR_KARTU + 2 * pad
    tinggi_pelat = QR_KARTU + pad + 7.2 * mm
    x_pelat = x + (w - lebar_pelat) / 2
    y_pelat = y + 7.2 * mm
    c.setFillColor(colors.black)
    c.setFillAlpha(0.18)
    c.roundRect(x_pelat + 0.5 * mm, y_pelat - 0.8 * mm, lebar_pelat, tinggi_pelat, 3 * mm, stroke=0, fill=1)
    c.setFillAlpha(1)
    c.setFillColor(colors.white)
    c.roundRect(x_pelat, y_pelat, lebar_pelat, tinggi_pelat, 3 * mm, stroke=0, fill=1)
    gambar_qr(c, tk.isi_qr_peserta(p.qr_token), x_pelat + pad, y_pelat + tinggi_pelat - pad - QR_KARTU, QR_KARTU)
    c.setFillColor(NAVY)
    c.setFont("Courier-Bold", 11.5)
    c.drawCentredString(x + w / 2, y_pelat + 2.6 * mm, p.kode_kartu or "")

    # 7. Kaki: teks di atas warna.
    c.setFillColor(teks)
    c.setFont("Helvetica-Bold", 5.2)
    c.drawString(x + tepi, y + 3 * mm, "KARTU WAJIB DIPAKAI SELAMA KEGIATAN")
    c.drawRightString(x + w - tepi, y + 3 * mm, f"{p.kontingen.kode} · v{p.versi_kartu}")
    c.restoreState()

    # Garis tepi tipis kartu (panduan potong).
    c.setStrokeColor(GARIS)
    c.setLineWidth(0.4)
    c.roundRect(x, y, w, h, radius, stroke=1, fill=0)
    return QR_KARTU


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
