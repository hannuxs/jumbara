"""Superadmin: kartu peserta, QR kontingen, kunci data biodata (Tahap 2)."""

from __future__ import annotations

import io
import re
import zipfile

from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.akun.decorators import superadmin_wajib
from apps.biodata.models import Peserta
from apps.inti.log import catat
from apps.kontingen.models import URUTAN_TINGKAT, Kontingen

from . import pdf, services
from .models import AlasanKartu, KartuRiwayat


def _nama_file(teks: str) -> str:
    teks = re.sub(r"[^\w\s-]", "", teks, flags=re.ASCII).strip()
    return re.sub(r"\s+", "_", teks)[:60]


def _pdf(isi: bytes, nama: str) -> HttpResponse:
    respons = HttpResponse(isi, content_type="application/pdf")
    respons["Content-Disposition"] = f'attachment; filename="{nama}"'
    return respons


def _kembali(request, cadangan: str):
    tujuan = request.POST.get("kembali", "")
    if tujuan.startswith("/superadmin/"):
        return redirect(tujuan)
    return redirect(cadangan)


@superadmin_wajib
def beranda(request):
    baris = Kontingen.objects.annotate(
        jumlah=Count("peserta", filter=Q(peserta__dihapus_pada__isnull=True)),
        ulang=Count("peserta", filter=Q(peserta__dihapus_pada__isnull=True, peserta__perlu_cetak_ulang=True)),
        nonaktif=Count("peserta", filter=Q(peserta__dihapus_pada__isnull=True, peserta__kartu_aktif=False)),
    ).order_by(URUTAN_TINGKAT, "kode")
    total = Peserta.objects.count()
    return render(
        request,
        "superadmin/kartu.html",
        {
            "menu_aktif": "kartu",
            "baris": baris,
            "terkunci": services.data_terkunci(),
            "total": total,
            "total_ulang": Peserta.objects.filter(perlu_cetak_ulang=True).count(),
            "tanpa_foto": Peserta.objects.filter(foto_path="").count(),
            "tanpa_token": Peserta.objects.filter(qr_token__isnull=True).count(),
        },
    )


@superadmin_wajib
@require_POST
def atur_kunci(request):
    kunci = request.POST.get("kunci") == "1"
    services.atur_kunci(request, kunci)
    if kunci:
        messages.success(
            request, "Data biodata dikunci. Form publik tertutup; perubahan berikutnya ditandai perlu cetak ulang."
        )
    else:
        messages.success(request, "Kunci data dibuka. Form publik kembali mengikuti jadwal di Pengaturan form.")
    return redirect("kartu_admin:beranda")


def _peserta_kontingen(k: Kontingen, hanya_ulang: bool):
    qs = Peserta.objects.filter(kontingen=k).select_related("kontingen")
    if hanya_ulang:
        qs = qs.filter(perlu_cetak_ulang=True)
    return list(qs)


@superadmin_wajib
def unduh_kontingen(request, pk: int):
    k = get_object_or_404(Kontingen, pk=pk)
    hanya_ulang = request.GET.get("ulang") == "1"
    daftar = _peserta_kontingen(k, hanya_ulang)
    if not daftar:
        messages.info(request, f"Tidak ada kartu {'yang perlu dicetak ulang ' if hanya_ulang else ''}untuk {k.nama}.")
        return redirect("kartu_admin:beranda")
    judul = "Kartu Cetak Ulang" if hanya_ulang else "Kartu Peserta"
    isi = pdf.kartu_pdf(daftar, judul, kontingen=k)
    catat(request, "kartu.diunduh", k, keterangan=f"PDF {judul.lower()} {k.kode}, {len(daftar)} kartu")
    awalan = "Kartu_Cetak_Ulang" if hanya_ulang else "Kartu"
    return _pdf(isi, f"{awalan}_{k.kode}_{_nama_file(k.nama)}.pdf")


@superadmin_wajib
def unduh_semua(request):
    """ZIP berisi satu PDF kartu per kontingen."""
    hanya_ulang = request.GET.get("ulang") == "1"
    buf = io.BytesIO()
    jumlah_kartu = jumlah_file = 0
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for k in Kontingen.objects.order_by(URUTAN_TINGKAT, "kode"):
            daftar = _peserta_kontingen(k, hanya_ulang)
            if not daftar:
                continue
            judul = "Kartu Cetak Ulang" if hanya_ulang else "Kartu Peserta"
            awalan = "Kartu_Cetak_Ulang" if hanya_ulang else "Kartu"
            z.writestr(f"{awalan}_{k.kode}_{_nama_file(k.nama)}.pdf", pdf.kartu_pdf(daftar, judul, kontingen=k))
            jumlah_kartu += len(daftar)
            jumlah_file += 1
    if not jumlah_file:
        messages.info(request, "Tidak ada kartu untuk diunduh.")
        return redirect("kartu_admin:beranda")
    catat(
        request,
        "kartu.diunduh",
        keterangan=f"ZIP {'cetak ulang ' if hanya_ulang else ''}{jumlah_file} kontingen, {jumlah_kartu} kartu",
    )
    respons = HttpResponse(buf.getvalue(), content_type="application/zip")
    nama = "Kartu_Cetak_Ulang_Semua" if hanya_ulang else "Kartu_Semua_Kontingen"
    respons["Content-Disposition"] = f'attachment; filename="{nama}_{timezone.localtime():%Y%m%d_%H%M}.zip"'
    return respons


@superadmin_wajib
def unduh_peserta(request, pk: int):
    """Satu kartu (cetak ulang) di posisi 1 dari 4 pada lembar F4."""
    p = get_object_or_404(Peserta.objects.select_related("kontingen"), pk=pk)
    isi = pdf.kartu_pdf([p], f"Kartu {p.kode_pendaftaran}")
    catat(request, "kartu.diunduh", p, keterangan=f"PDF kartu satu orang {p.kode_pendaftaran} ({p.kode_kartu})")
    return _pdf(isi, f"Kartu_{p.kontingen.kode}_{_nama_file(p.nama_lengkap)}_{p.kode_pendaftaran}.pdf")


@superadmin_wajib
def unduh_qr(request, pk: int | None = None):
    if pk is not None:
        daftar = [get_object_or_404(Kontingen, pk=pk)]
        nama = f"QR_Kontingen_{daftar[0].kode}_{_nama_file(daftar[0].nama)}.pdf"
    else:
        daftar = list(Kontingen.objects.order_by(URUTAN_TINGKAT, "kode"))
        nama = "QR_Kontingen_Semua.pdf"
    isi = pdf.qr_kontingen_pdf(daftar)
    catat(request, "kontingen.qr_diunduh", keterangan=f"PDF QR kontingen: {', '.join(k.kode for k in daftar)}"[:255])
    return _pdf(isi, nama)


@superadmin_wajib
@require_POST
def tandai_tercetak(request):
    """Hapus tanda perlu cetak ulang setelah kartu dicetak (per orang, per kontingen, atau semua)."""
    qs = Peserta.objects.all()
    keterangan = "semua kontingen"
    if request.POST.get("peserta"):
        qs = qs.filter(pk=request.POST["peserta"])
        keterangan = "satu orang"
    elif request.POST.get("kontingen"):
        k = get_object_or_404(Kontingen, pk=request.POST["kontingen"])
        qs = qs.filter(kontingen=k)
        keterangan = k.kode
    jumlah = services.tandai_tercetak(request, qs, keterangan)
    messages.success(request, f"{jumlah} kartu ditandai sudah dicetak ulang.")
    return _kembali(request, "kartu_admin:beranda")


@superadmin_wajib
@require_POST
def terbitkan_ulang(request, pk: int):
    p = get_object_or_404(Peserta, pk=pk)
    alasan = request.POST.get("alasan", "")
    if alasan not in AlasanKartu.values:
        messages.error(request, "Pilih alasan kartu baru.")
        return redirect("biodata_admin:detail", pk=p.pk)
    lama = p.kode_kartu
    p = services.terbitkan_ulang(request, p, alasan)
    messages.success(
        request, f"Kartu {lama} dinonaktifkan. Kartu baru {p.kode_kartu} (versi {p.versi_kartu}) siap dicetak."
    )
    return redirect("biodata_admin:detail", pk=p.pk)


@superadmin_wajib
@require_POST
def atur_aktif(request, pk: int):
    p = get_object_or_404(Peserta, pk=pk)
    aktif = request.POST.get("aktif") == "1"
    services.atur_aktif(request, p, aktif)
    messages.success(request, f"Kartu {p.kode_kartu} {'diaktifkan' if aktif else 'dinonaktifkan'}.")
    return redirect("biodata_admin:detail", pk=p.pk)


@superadmin_wajib
@require_POST
def ganti_qr_kontingen(request, pk: int):
    k = get_object_or_404(Kontingen, pk=pk)
    services.ganti_qr_kontingen(request, k)
    messages.success(request, f"QR kontingen {k.kode} diganti. Cetak ulang lembar QR tenda; QR lama tidak berlaku.")
    return redirect("kontingen_admin:detail", pk=k.pk)


def riwayat_kartu(peserta: Peserta):
    return KartuRiwayat.objects.filter(peserta=peserta).order_by("-dibuat_pada")
