"""PDF bukti pendaftaran (ReportLab). Tanpa NIK dan tanpa data pribadi lain."""

from __future__ import annotations

import io
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A6
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from apps.inti.utils import jam_id, tanggal_id

from .models import Peserta

FOLDER_IMG = Path(settings.BASE_DIR) / "static" / "img"
# Logo PMI mendatar berlatar putih (R13, 25 Okt 2026). Jangan diubah bentuk/warnanya.
LOGO_PMI = "pmi-logo-cetak.png"
ORANYE = colors.HexColor("#F26B1D")
NAVY = colors.HexColor("#1F2937")
ABU = colors.HexColor("#6B7280")
KREM = colors.HexColor("#FFF3E4")


def _logo(
    c: canvas.Canvas, nama: str, x: float, y: float, tinggi: float, kanan: bool = False, lebar_maks: float | None = None
) -> None:
    """Logo setinggi `tinggi`; bila lebih lebar dari `lebar_maks`, dikecilkan dan ditengahkan tegak."""
    img = ImageReader(str(FOLDER_IMG / nama))
    lebar_asli, tinggi_asli = img.getSize()
    tinggi_pakai = tinggi
    if lebar_maks:
        tinggi_pakai = min(tinggi, lebar_maks * tinggi_asli / lebar_asli)
    lebar = tinggi_pakai * lebar_asli / tinggi_asli
    y += (tinggi - tinggi_pakai) / 2
    c.drawImage(img, x - lebar if kanan else x, y, width=lebar, height=tinggi_pakai, mask="auto")


def bukti_pendaftaran(peserta: Peserta) -> bytes:
    buf = io.BytesIO()
    lebar, tinggi = A6
    c = canvas.Canvas(buf, pagesize=A6)
    c.setTitle(f"Bukti Pendaftaran {peserta.kode_pendaftaran}")
    c.setAuthor("SIGAP JUMBARA")

    # Kepala putih: logo PMI kiri, logo Jumbara V kanan.
    tepi = 7 * mm
    atas = tinggi - tepi
    # Logo PMI mendatar: lebarnya dibatasi agar tidak menabrak judul di tengah.
    ruang_kiri = lebar / 2 - stringWidth("KABUPATEN BULUNGAN V 2026", "Helvetica-Bold", 8) / 2 - tepi - 2 * mm
    _logo(c, LOGO_PMI, tepi, atas - 14 * mm, 14 * mm, lebar_maks=ruang_kiri)
    _logo(c, "jumbara-v-400.jpg", lebar - tepi, atas - 14 * mm, 14 * mm, kanan=True)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(lebar / 2, atas - 5 * mm, "JUMBARA PMR TINGKAT")
    c.drawCentredString(lebar / 2, atas - 8.5 * mm, "KABUPATEN BULUNGAN V 2026")
    c.setFont("Helvetica", 6.5)
    c.setFillColor(ABU)
    c.drawCentredString(lebar / 2, atas - 12 * mm, "Unggul - Responsif - Berkarakter")

    # Pita judul oranye.
    y = atas - 22 * mm
    c.setFillColor(ORANYE)
    c.roundRect(tepi, y, lebar - 2 * tepi, 7 * mm, 2 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawCentredString(lebar / 2, y + 2.3 * mm, "BUKTI PENDAFTARAN BIODATA")

    # Kode pendaftaran besar.
    y -= 17 * mm
    c.setFillColor(KREM)
    c.roundRect(tepi, y, lebar - 2 * tepi, 14 * mm, 2 * mm, stroke=0, fill=1)
    c.setFillColor(ABU)
    c.setFont("Helvetica", 7)
    c.drawCentredString(lebar / 2, y + 10 * mm, "Kode pendaftaran")
    c.setFillColor(NAVY)
    c.setFont("Courier-Bold", 18)
    c.drawCentredString(lebar / 2, y + 3 * mm, peserta.kode_pendaftaran)

    baris = [
        ("Nama", peserta.nama_lengkap.upper()),
        ("Sekolah", peserta.kontingen.nama),
        ("Tingkat", peserta.get_tingkat_display()),
        ("Peran", peserta.get_peran_display()),
        ("Dikirim", f"{tanggal_id(peserta.dibuat_pada)}, {jam_id(peserta.dibuat_pada)}"),
    ]
    y -= 6 * mm
    lebar_isi = lebar - 2 * tepi - 18 * mm
    for label, isi in baris:
        c.setFillColor(ABU)
        c.setFont("Helvetica", 7.5)
        c.drawString(tepi, y, label)
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 8.5)
        for potong in simpleSplit(isi, "Helvetica-Bold", 8.5, lebar_isi):
            c.drawString(tepi + 18 * mm, y, potong)
            y -= 4.2 * mm
        y -= 1.3 * mm

    y -= 2 * mm
    c.setFillColor(ABU)
    c.setFont("Helvetica", 6.8)
    catatan = "Simpan bukti ini. Jika ada data yang salah, hubungi superadmin dan sebutkan kode pendaftaran di atas."
    for potong in simpleSplit(catatan, "Helvetica", 6.8, lebar - 2 * tepi):
        c.drawString(tepi, y, potong)
        y -= 3.4 * mm
    c.setFont("Helvetica", 6)
    c.drawString(tepi, 6 * mm, f"Dicetak {tanggal_id(timezone.now(), hari=False)} · SIGAP JUMBARA")
    c.showPage()
    c.save()
    return buf.getvalue()
