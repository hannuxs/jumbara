"""Poster QR link Anjangsana (dipajang di sekretariat, dibagikan ke grup pimpinan)."""

from __future__ import annotations

import io

from django.conf import settings
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

from apps.inti.utils import tanggal_id
from apps.kartu.pdf import F4, NAVY, ORANYE, _kaki_lembar, _kepala_halaman, gambar_qr

from .models import SesiAnjangsana


def url_anjangsana() -> str:
    return f"{settings.SIGAP_URL}/anjangsana/"


def poster_pdf() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=F4)
    c.setTitle("Poster Anjangsana Jumbara V 2026")
    c.setAuthor("SIGAP JUMBARA")
    tengah = F4[0] / 2
    y = _kepala_halaman(c, F4[1] - 14 * mm, 24 * mm) - 16 * mm
    c.setFillColor(ORANYE)
    c.setFont("Helvetica-Bold", 44)
    c.drawCentredString(tengah, y, "ANJANGSANA")
    y -= 10 * mm
    c.setFillColor(NAVY)
    c.setFont("Helvetica", 15)
    c.drawCentredString(tengah, y, "Buku tamu dan review antarkontingen")
    ukuran_qr = 135 * mm
    y_qr = y - 8 * mm - ukuran_qr
    gambar_qr(c, url_anjangsana(), (F4[0] - ukuran_qr) / 2, y_qr, ukuran_qr, tepi_modul=3)
    y = y_qr - 8 * mm
    c.setFont("Courier-Bold", 15)
    c.drawCentredString(tengah, y, url_anjangsana())
    y -= 11 * mm
    c.setFont("Helvetica-Bold", 13)
    c.drawString(25 * mm, y, "Cara mengisi:")
    c.setFont("Helvetica", 12)
    langkah = [
        "1. Pindai QR di atas dengan kamera HP, buka link-nya.",
        '2. Tekan "Pindai kartu saya", lalu pindai QR di kartu peserta Anda.',
        "3. Di tenda tuan rumah, pindai QR kontingen yang ditempel di sana.",
        "4. Beri nilai 1-5 untuk Pengetahuan, Keterampilan, dan Sikap, lalu kirim.",
        "Satu kontingen tamu memberi satu review untuk setiap tuan rumah.",
    ]
    for teks in langkah:
        for b in simpleSplit(teks, "Helvetica", 12, F4[0] - 50 * mm):
            y -= 6 * mm
            c.drawString(25 * mm, y, b)
    sesi = list(SesiAnjangsana.objects.all())
    if sesi:
        y -= 10 * mm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(25 * mm, y, "Jadwal sesi (WITA):")
        c.setFont("Helvetica", 11)
        per_tanggal: dict = {}
        for s in sesi:
            per_tanggal.setdefault(s.tanggal, []).append(f"{s.mulai:%H.%M}-{s.selesai:%H.%M}")
        for tgl, jam in per_tanggal.items():
            y -= 5.5 * mm
            c.drawString(25 * mm, y, f"{tanggal_id(tgl)}: {', '.join(jam)}")
    _kaki_lembar(c, "SIGAP JUMBARA · Link hanya aktif selama sesi Anjangsana.")
    c.showPage()
    c.save()
    return buf.getvalue()
