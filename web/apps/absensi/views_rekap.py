"""Rekap kehadiran dan poin (superadmin dan panitia; tanpa data pribadi). Semua bisa diunduh Excel."""

from __future__ import annotations

import io
from datetime import date

import xlsxwriter
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from apps.akun.decorators import peran_wajib
from apps.biodata.models import Peserta
from apps.inti.log import catat
from apps.inti.models import Tingkat
from apps.kontingen.models import URUTAN_TINGKAT, Kontingen

from . import rekap
from .models import Kegiatan, Kehadiran, TitikAbsen

boleh = peran_wajib("SUPERADMIN", "PANITIA")
TIPE_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def excel(
    request, judul: str, kepala: list[str], baris: list[list], nama: str, lebar: list[int] | None = None
) -> HttpResponse:
    """Satu sheet: judul di baris pertama, waktu unduh, lalu tabel dengan saringan."""
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True, "remove_timezone": True})
    ws = wb.add_worksheet("Rekap")
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
    ws.write(0, 0, judul, f_judul)
    ws.write(1, 0, f"Jumbara PMR Kab. Bulungan V 2026 · diunduh {timezone.localtime():%d/%m/%Y %H.%M} WITA")
    for i, k in enumerate(kepala):
        ws.write(3, i, k, f_kepala)
        ws.set_column(i, i, (lebar[i] if lebar and i < len(lebar) else max(10, min(40, len(k) + 4))))
    for r, b in enumerate(baris, start=4):
        ws.write_row(r, 0, b)
    ws.freeze_panes(4, 0)
    if baris:
        ws.autofilter(3, 0, 3 + len(baris), len(kepala) - 1)
    wb.close()
    catat(request, "rekap.diunduh", keterangan=judul[:255])
    respons = HttpResponse(buf.getvalue(), content_type=TIPE_XLSX)
    respons["Content-Disposition"] = f'attachment; filename="{nama}_{timezone.localtime():%Y%m%d_%H%M}.xlsx"'
    return respons


def _unduh(request) -> bool:
    return request.GET.get("unduh") == "xlsx"


def _sel(p) -> str:
    return f"{p.hadir}/{p.kuota if p.kuota is not None else '-'}"


@boleh
def beranda(request):
    tingkat = request.GET.get("tingkat") if request.GET.get("tingkat") in Tingkat.values else "MULA"
    data = rekap.rekap_tingkat(tingkat)
    label = Tingkat(tingkat).label
    if _unduh(request):
        return excel(
            request, f"Rekap tingkat {label}",
            ["Kode", "Titik absen", "Tanggal", "Jam", "Hadir", "Kontingen hadir", "Total kontingen", "Kuota total", "Persen"],
            [[d["titik"].kode, d["titik"].nama_tampil, d["titik"].tanggal.strftime("%d/%m/%Y"), f"{d['titik'].mulai:%H.%M}",
              d["hadir"], d["kontingen_hadir"], d["kontingen_total"], d["kuota"] if d["kuota"] is not None else "-",
              d["persen"] if d["persen"] is not None else "-"] for d in data],
            f"Rekap_{label}", [9, 45, 12, 8, 8, 10, 10, 10, 8],
        )  # fmt: skip
    return render(
        request, "rekap/tingkat.html", {"tab": "tingkat", "tingkat": tingkat, "data": data, "pilihan": Tingkat.choices}
    )


@boleh
def titik(request, pk: int):
    t = get_object_or_404(TitikAbsen.objects.select_related("kegiatan"), pk=pk)
    data = rekap.rekap_titik(t)
    if _unduh(request):
        baris = [[k.diterima_pada.astimezone(timezone.get_current_timezone()).strftime("%H.%M.%S"), k.peserta.nama_lengkap,
                  k.peserta.kontingen.kode, k.peserta.kontingen.nama, k.peserta.get_peran_display(), k.nama_pemindai,
                  k.get_metode_display()] for k in data["hadir"]]  # fmt: skip
        baris.append([])
        baris.append(["Kontingen", "Nama", "Hadir", "Kuota", "Status"])
        baris += [
            [b["k"].kode, b["k"].nama, b["p"].hadir, b["p"].kuota if b["p"].kuota is not None else "-", b["status"]]
            for b in data["kontingen"]
        ]
        return excel(request, f"Rekap {t.kode} {t.nama_tampil} ({t.tanggal:%d/%m/%Y})",
                     ["Jam", "Nama", "Kode", "Kontingen", "Peran", "Pemindai", "Metode"], baris, f"Rekap_{t.kode}",
                     [10, 32, 8, 34, 18, 14, 10])  # fmt: skip
    return render(request, "rekap/titik.html", {"tab": "tingkat", "t": t, "data": data})


@boleh
def kegiatan_daftar(request):
    return render(request, "rekap/kegiatan_daftar.html", {"tab": "kegiatan", "kegiatan": Kegiatan.objects.all()})


@boleh
def kegiatan(request, pk: int):
    kg = get_object_or_404(Kegiatan, pk=pk)
    tingkat = request.GET.get("tingkat") if request.GET.get("tingkat") in Tingkat.values else "MULA"
    titik_list, baris = rekap.tabel_poin_kegiatan(kg, tingkat)
    if _unduh(request):
        kepala = (
            ["Kode", "Kontingen"]
            + [f"{t.kode} {t.tanggal:%d/%m} (hadir/kuota)" for t in titik_list]
            + [f"Poin {t.kode}" for t in titik_list]
            + ["Total hadir", "Poin kehadiran"]
        )
        isi = [
            [b.kontingen.kode, b.kontingen.nama]
            + [_sel(p) for _, p in b.sesi]
            + [p.poin for _, p in b.sesi]
            + [b.total_hadir, b.total]
            for b in baris
        ]
        return excel(
            request,
            f"Poin kehadiran {kg.nama} - tingkat {Tingkat(tingkat).label}",
            kepala,
            isi,
            f"Poin_{kg.kode}_{tingkat}",
        )
    return render(
        request, "rekap/kegiatan.html",
        {"tab": "kegiatan", "kg": kg, "tingkat": tingkat, "titik": titik_list, "baris": baris, "pilihan": Tingkat.choices,
         "batasi": rekap.batasi_ke_kuota()},
    )  # fmt: skip


@boleh
def kontingen_daftar(request):
    return render(
        request,
        "rekap/kontingen_daftar.html",
        {"tab": "kontingen", "kontingen": Kontingen.objects.order_by(URUTAN_TINGKAT, "kode")},
    )


@boleh
def kontingen(request, pk: int):
    k = get_object_or_404(Kontingen, pk=pk)
    data = rekap.rekap_kontingen(k)
    if _unduh(request):
        isi = [[b["titik"].kode, b["titik"].nama_tampil, b["titik"].tanggal.strftime("%d/%m/%Y"), f"{b['titik'].mulai:%H.%M}",
                b["p"].hadir, b["p"].kuota if b["p"].kuota is not None else "-", b["p"].poin if b["titik"].hitung_poin else "-"]
               for b in data["baris"]]  # fmt: skip
        isi += [[], ["Belum daftar ulang"]] + [
            [p.nama_lengkap, p.get_peran_display()] for p in data["daftar_ulang"]["belum"]
        ]
        return excel(request, f"Rekap kontingen {k.kode} {k.nama}", ["Kode", "Titik absen", "Tanggal", "Jam", "Hadir", "Kuota", "Poin"],
                     isi, f"Rekap_{k.kode}", [9, 45, 12, 8, 8, 8, 8])  # fmt: skip
    return render(request, "rekap/kontingen.html", {"tab": "kontingen", "k": k, "data": data})


@boleh
def orang(request, pk: int | None = None):
    q = " ".join(request.GET.get("q", "").split())[:60]
    hasil = (
        list(Peserta.objects.filter(nama_lengkap__icontains=q).select_related("kontingen")[:30]) if len(q) >= 2 else []
    )
    p = get_object_or_404(Peserta.objects.select_related("kontingen"), pk=pk) if pk else None
    riwayat = (
        Kehadiran.objects.filter(peserta=p)
        .select_related("titik_absen")
        .order_by("titik_absen__tanggal", "titik_absen__mulai")
        if p
        else []
    )
    return render(request, "rekap/orang.html", {"tab": "orang", "q": q, "hasil": hasil, "p": p, "riwayat": riwayat})


@boleh
def harian(request):
    daftar_tanggal = list(TitikAbsen.objects.order_by("tanggal").values_list("tanggal", flat=True).distinct())
    try:
        tanggal = date.fromisoformat(request.GET.get("tanggal", ""))
    except ValueError:
        hari_ini = timezone.localdate()
        tanggal = hari_ini if hari_ini in daftar_tanggal else (daftar_tanggal[0] if daftar_tanggal else hari_ini)
    data = rekap.rekap_harian(tanggal)
    if _unduh(request):
        isi = []
        for blok in data:
            isi.append([f"Tingkat {Tingkat(blok['tingkat']).label}"])
            isi.append(["Kode", "Kontingen"] + [f"{t.kode} {t.mulai:%H.%M} {t.nama_tampil}" for t in blok["titik"]])
            isi += [[b["k"].kode, b["k"].nama] + [_sel(p) for p in b["sel"]] for b in blok["baris"]]
            isi.append([])
        return excel(
            request,
            f"Rekap harian {tanggal:%d/%m/%Y} (hadir/kuota)",
            ["", ""],
            isi,
            f"Rekap_harian_{tanggal:%Y%m%d}",
            [9, 34],
        )
    return render(
        request,
        "rekap/harian.html",
        {"tab": "harian", "tanggal": tanggal, "daftar_tanggal": daftar_tanggal, "data": data},
    )


@boleh
def daftar_ulang(request):
    data = rekap.rekap_daftar_ulang()
    if _unduh(request):
        return excel(request, "Rekap daftar ulang", ["Kode", "Kontingen", "Tingkat", "Biodata", "Sudah daftar ulang", "Belum (kartu belum diambil)"],
                     [[d["k"].kode, d["k"].nama, d["k"].get_tingkat_display(), d["biodata"], d["sudah"], d["belum"]] for d in data],
                     "Rekap_daftar_ulang", [9, 36, 10, 10, 14, 18])  # fmt: skip
    total = {
        "biodata": sum(d["biodata"] for d in data),
        "sudah": sum(d["sudah"] for d in data),
        "belum": sum(d["belum"] for d in data),
    }
    return render(request, "rekap/daftar_ulang.html", {"tab": "daftar_ulang", "data": data, "total": total})
