"""Menggambar piagam ke PDF (ReportLab). Koordinat elemen dalam mm dari KIRI ATAS halaman;
`y` adalah garis dasar (baseline) baris pertama teks."""

from __future__ import annotations

import io
import re
from pathlib import Path

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .models import Orientasi, TemplatePiagam, UkuranKertas

FOLDER_FONT = Path(__file__).resolve().parent / "fonts"
FOLDER_IMG = Path(settings.BASE_DIR) / "static" / "img"

# Pilihan huruf: kode -> (label, nama font ReportLab, file TTF atau None untuk font bawaan PDF).
HURUF = {
    "POPPINS_TEBAL": ("Poppins tebal", "Poppins-Bold", "poppins-latin-700.ttf"),
    "POPPINS_SEMI": ("Poppins semi tebal", "Poppins-SemiBold", "poppins-latin-600.ttf"),
    "POPPINS": ("Poppins biasa", "Poppins", "poppins-latin-400.ttf"),
    "INTER_TEBAL": ("Inter tebal", "Inter-Bold", "inter-latin-700.ttf"),
    "INTER_SEMI": ("Inter semi tebal", "Inter-SemiBold", "inter-latin-600.ttf"),
    "INTER": ("Inter biasa", "Inter", "inter-latin-400.ttf"),
    "SERIF_TEBAL_MIRING": ("Serif tebal miring (Times)", "Times-BoldItalic", None),
    "SERIF_TEBAL": ("Serif tebal (Times)", "Times-Bold", None),
    "SERIF_MIRING": ("Serif miring (Times)", "Times-Italic", None),
    "SERIF": ("Serif (Times)", "Times-Roman", None),
}
RATA = ("KIRI", "TENGAH", "KANAN")
_terdaftar: set[str] = set()


def nama_font(kode: str) -> str:
    label, nama, berkas = HURUF.get(kode, HURUF["INTER"])
    if berkas and nama not in _terdaftar:
        pdfmetrics.registerFont(TTFont(nama, str(FOLDER_FONT / berkas)))
        _terdaftar.add(nama)
    return nama


def ukuran_halaman(t: TemplatePiagam) -> tuple[float, float]:
    lebar, tinggi = (210 * mm, 297 * mm) if t.ukuran_kertas == UkuranKertas.A4 else (215 * mm, 330 * mm)
    return (tinggi, lebar) if t.orientasi == Orientasi.MENDATAR else (lebar, tinggi)


_PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")


def isi_teks(pola: str, data: dict) -> str:
    """Ganti {kunci} dengan data (tanpa format()/eval). Kunci tak dikenal dibiarkan apa adanya."""
    return _PLACEHOLDER.sub(lambda m: str(data.get(m.group(1), m.group(0))), pola or "")


def warna(teks: str, bawaan="#1F2937"):
    try:
        return colors.HexColor(teks if re.fullmatch(r"#[0-9A-Fa-f]{6}", teks or "") else bawaan)
    except ValueError:
        return colors.HexColor(bawaan)


# --- Desain bawaan (dipakai sampai desain panitia diunggah) ---------------------------------------------


def desain_bawaan(c: canvas.Canvas, w: float, h: float) -> None:
    oranye, merah, navy = colors.HexColor("#F26B1D"), colors.HexColor("#C62828"), colors.HexColor("#1F2937")
    c.setFillColor(colors.HexColor("#FFFCF7"))
    c.rect(0, 0, w, h, stroke=0, fill=1)
    # Sudut segitiga bergradasi.
    for sx, sy in ((0, h), (w, 0)):
        c.saveState()
        p = c.beginPath()
        arah_x = 1 if sx == 0 else -1
        arah_y = -1 if sy == h else 1
        p.moveTo(sx, sy)
        p.lineTo(sx + arah_x * 70 * mm, sy)
        p.lineTo(sx, sy + arah_y * 70 * mm)
        p.close()
        c.clipPath(p, stroke=0, fill=0)
        c.linearGradient(sx, sy, sx + arah_x * 45 * mm, sy + arah_y * 45 * mm, [merah, oranye], extend=True)
        c.restoreState()
    c.setFillColor(oranye)
    c.setFillAlpha(0.07)
    c.circle(w / 2, h / 2, min(w, h) * 0.32, stroke=0, fill=1)
    c.setFillAlpha(1)
    # Bingkai ganda.
    c.setStrokeColor(oranye)
    c.setLineWidth(2.4)
    c.roundRect(9 * mm, 9 * mm, w - 18 * mm, h - 18 * mm, 3 * mm, stroke=1, fill=0)
    c.setStrokeColor(navy)
    c.setLineWidth(0.6)
    c.roundRect(12.5 * mm, 12.5 * mm, w - 25 * mm, h - 25 * mm, 2 * mm, stroke=1, fill=0)
    # Pita bawah tipis.
    c.setFillColor(oranye)
    c.rect(w / 2 - 40 * mm, 12.5 * mm, 80 * mm, 1.2 * mm, stroke=0, fill=1)


def tempel_logo(c: canvas.Canvas, t: TemplatePiagam, w: float, h: float) -> None:
    tinggi = max(8.0, min(60.0, t.logo_tinggi)) * mm
    gambar = [str(FOLDER_IMG / "pmi-logo-160.png"), str(FOLDER_IMG / "jumbara-v-400.jpg")]
    lebar = [tinggi * ImageReader(g).getSize()[0] / ImageReader(g).getSize()[1] for g in gambar]
    jarak = 6 * mm
    total = sum(lebar) + jarak
    x = (w - total) / 2 if not t.logo_x else t.logo_x * mm
    y = h - t.logo_y * mm - tinggi
    for g, lb in zip(gambar, lebar, strict=True):
        c.drawImage(g, x, y, width=lb, height=tinggi, mask="auto")
        x += lb + jarak


# --- Elemen teks ---------------------------------------------------------------------------------------------


def gambar_elemen(c: canvas.Canvas, e: dict, data: dict, w: float, h: float) -> None:
    teks = isi_teks(e.get("teks", ""), data).strip()
    if not teks:
        return
    font = nama_font(e.get("font", "INTER"))
    ukuran = float(e.get("ukuran") or 14)
    ukuran_min = min(ukuran, float(e.get("ukuran_min") or max(6.0, ukuran * 0.6)))
    lebar = float(e.get("lebar") or 200) * mm
    baris_maks = max(1, int(e.get("baris_maks") or 1))
    if e.get("kapital"):
        teks = teks.upper()
    # Kecilkan huruf sampai muat (lebar untuk 1 baris, jumlah baris untuk teks panjang).
    while True:
        baris = simpleSplit(teks, font, ukuran, lebar) if baris_maks > 1 else [teks]
        muat = len(baris) <= baris_maks and all(stringWidth(b, font, ukuran) <= lebar for b in baris)
        if muat or ukuran <= ukuran_min:
            break
        ukuran = max(ukuran_min, ukuran - 0.5)
    c.setFillColor(warna(e.get("warna", "")))
    c.setFont(font, ukuran)
    x = float(e.get("x") or 0) * mm
    y = h - float(e.get("y") or 0) * mm
    rata = e.get("rata", "TENGAH")
    for b in baris[:baris_maks]:
        if rata == "KIRI":
            c.drawString(x, y, b)
        elif rata == "KANAN":
            c.drawRightString(x + lebar, y, b)
        else:
            c.drawCentredString(x + lebar / 2, y, b)
        y -= ukuran * 1.3


def path_latar(t: TemplatePiagam) -> Path | None:
    if not t.latar or not re.fullmatch(r"[0-9a-f]{32}\.(png|jpg)", t.latar):
        return None
    p = Path(settings.SIGAP_FOLDER_PRIVAT) / "piagam" / t.latar
    return p if p.is_file() else None


def gambar_halaman(c: canvas.Canvas, t: TemplatePiagam, data: dict) -> None:
    w, h = ukuran_halaman(t)
    latar = path_latar(t)
    if latar is not None:
        c.drawImage(str(latar), 0, 0, width=w, height=h)  # path string: gambar disimpan sekali per PDF
    elif t.desain_bawaan:
        desain_bawaan(c, w, h)
    if t.tempel_logo:
        tempel_logo(c, t, w, h)
    for e in t.elemen or []:
        gambar_elemen(c, e, data, w, h)


def buat_pdf(daftar: list[tuple[TemplatePiagam, dict]], judul: str = "Piagam Jumbara V 2026") -> bytes:
    """Satu PDF, satu halaman per piagam (ukuran halaman mengikuti template masing-masing)."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.setTitle(judul)
    c.setAuthor("SIGAP JUMBARA")
    for t, data in daftar:
        c.setPageSize(ukuran_halaman(t))
        gambar_halaman(c, t, data)
        c.showPage()
    if not daftar:
        c.showPage()
    c.save()
    return buf.getvalue()


def pratinjau_png(t: TemplatePiagam, data: dict, lebar_px: int = 1100) -> bytes:
    """Gambar PNG halaman piagam untuk editor tata letak."""
    import pypdfium2 as pdfium

    pdf = buat_pdf([(t, data)])
    doc = pdfium.PdfDocument(pdf)
    halaman = doc[0]
    skala = lebar_px / halaman.get_width()
    img = halaman.render(scale=skala).to_pil()
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
