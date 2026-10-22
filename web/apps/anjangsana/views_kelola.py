"""Halaman Anjangsana untuk superadmin dan panitia: peringkat, kunjungan, review, sesi, poster."""

from __future__ import annotations

from django import forms
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.absensi.views_rekap import excel
from apps.akun.decorators import peran_wajib, superadmin_wajib
from apps.inti import pengaturan
from apps.inti.log import catat
from apps.inti.models import Tingkat
from apps.inti.pengaturan import StatusPaksa
from apps.kontingen.models import Kontingen

from . import services as svc
from .models import Kunjungan, Review, SesiAnjangsana
from .pdf import poster_pdf, url_anjangsana

boleh = peran_wajib("SUPERADMIN", "PANITIA")
PILIHAN_TINGKAT = [
    ("", "Gabungan semua tingkat"),
    (Tingkat.MULA, "Mula"),
    (Tingkat.MADYA, "Madya"),
    (Tingkat.WIRA, "Wira"),
]


def _unduh(request) -> bool:
    return request.GET.get("unduh") == "xlsx"


def _jam(dt) -> str:
    return f"{timezone.localtime(dt):%d/%m %H.%M}" if dt else ""


@boleh
def peringkat(request):
    tingkat = request.GET.get("tingkat", "")
    if tingkat not in dict(PILIHAN_TINGKAT):
        tingkat = ""
    hasil = svc.peringkat(tingkat or None)
    label = dict(PILIHAN_TINGKAT)[tingkat]
    if _unduh(request):
        return excel(
            request,
            f"Peringkat Anjangsana · {label}",
            [
                "Peringkat",
                "Kode",
                "Kontingen",
                "Tingkat",
                "Rata-rata nilai",
                "Jumlah review",
                "Kontingen tamu berbeda",
                "Jumlah kunjungan",
            ],
            [
                [
                    h["peringkat"],
                    h["k"].kode,
                    h["k"].nama,
                    h["k"].get_tingkat_display(),
                    h["rata_rata"],
                    h["jumlah_review"],
                    h["tamu_berbeda"],
                    h["jumlah_kunjungan"],
                ]
                for h in hasil
            ],  # fmt: skip
            "peringkat-anjangsana",
            [10, 9, 40, 10, 14, 12, 14, 12],
        )
    return render(request, "anjangsana/peringkat.html", {
        "tab": "anjangsana", "sub": "peringkat", "hasil": hasil, "tingkat": tingkat, "pilihan": PILIHAN_TINGKAT,
        "label": label, "st": svc.status(),
    })  # fmt: skip


def _saring_kontingen(request, qs, tamu: str, tuan: str):
    k = request.GET.get("k", "")
    if k.isdigit():
        arah = request.GET.get("arah", "")
        if arah == "tamu":
            qs = qs.filter(**{tamu: int(k)})
        elif arah == "tuan":
            qs = qs.filter(**{tuan: int(k)})
        else:
            qs = qs.filter(Q(**{tamu: int(k)}) | Q(**{tuan: int(k)}))
    return qs


@boleh
def kunjungan(request):
    qs = Kunjungan.objects.select_related("pengunjung", "kontingen_tamu", "kontingen_tuan_rumah").order_by(
        "-dipindai_pada"
    )
    qs = _saring_kontingen(request, qs, "kontingen_tamu_id", "kontingen_tuan_rumah_id")
    if _unduh(request):
        return excel(
            request,
            "Kunjungan Anjangsana",
            ["Waktu", "Pengunjung", "Kontingen tamu", "Kontingen tuan rumah"],
            [
                [_jam(x.dipindai_pada), x.pengunjung.nama_lengkap, x.kontingen_tamu.nama, x.kontingen_tuan_rumah.nama]
                for x in qs
            ],
            "kunjungan-anjangsana",
            [14, 30, 36, 36],
        )
    halaman = Paginator(qs, 50).get_page(request.GET.get("hal"))
    return render(request, "anjangsana/kunjungan.html", {
        "tab": "anjangsana", "sub": "kunjungan", "halaman": halaman, "total": qs.count(),
        "kontingen": Kontingen.objects.all(), "k": request.GET.get("k", ""), "arah": request.GET.get("arah", ""),
    })  # fmt: skip


@boleh
def review(request):
    qs = Review.objects.select_related("pengunjung", "kontingen_tamu", "kontingen_tuan_rumah").order_by("-dikirim_pada")
    qs = _saring_kontingen(request, qs, "kontingen_tamu_id", "kontingen_tuan_rumah_id")
    if _unduh(request):
        return excel(
            request,
            "Review Anjangsana",
            [
                "Waktu",
                "Kontingen tamu",
                "Kontingen tuan rumah",
                "Pengunjung",
                "Pengetahuan",
                "Keterampilan",
                "Sikap",
                "Rata-rata",
                "Komentar",
                "Pernah diganti",
            ],  # fmt: skip
            [
                [
                    _jam(r.dikirim_pada),
                    r.kontingen_tamu.nama,
                    r.kontingen_tuan_rumah.nama,
                    r.pengunjung.nama_lengkap if r.pengunjung else "",
                    r.nilai_pengetahuan,
                    r.nilai_keterampilan,
                    r.nilai_sikap,
                    round((r.nilai_pengetahuan + r.nilai_keterampilan + r.nilai_sikap) / 3, 2),
                    r.komentar,
                    len(r.riwayat or []),
                ]
                for r in qs
            ],  # fmt: skip
            "review-anjangsana",
            [14, 32, 32, 26, 11, 11, 9, 10, 50, 10],
        )
    halaman = Paginator(qs, 50).get_page(request.GET.get("hal"))
    return render(request, "anjangsana/review.html", {
        "tab": "anjangsana", "sub": "review", "halaman": halaman, "total": qs.count(),
        "kontingen": Kontingen.objects.all(), "k": request.GET.get("k", ""), "arah": request.GET.get("arah", ""),
    })  # fmt: skip


@superadmin_wajib
@require_POST
def review_hapus(request, pk: int):
    r = get_object_or_404(Review, pk=pk)
    svc.hapus_review(request, r)
    messages.success(
        request, f"Review {r.kontingen_tamu.nama} untuk {r.kontingen_tuan_rumah.nama} dipindahkan ke tempat sampah."
    )
    kembali = request.POST.get("kembali", "")
    return redirect(kembali if kembali.startswith("/rekap/anjangsana/") else "anjangsana_kelola:review")


# --- Superadmin: status, sesi, poster ---------------------------------------------------------------


class FormSesi(forms.ModelForm):
    class Meta:
        model = SesiAnjangsana
        fields = ["tanggal", "mulai", "selesai"]
        widgets = {
            "tanggal": forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
            "mulai": forms.TimeInput(attrs={"type": "time", "class": "input"}, format="%H:%M"),
            "selesai": forms.TimeInput(attrs={"type": "time", "class": "input"}, format="%H:%M"),
        }

    def clean(self):
        data = super().clean()
        mulai, selesai, tanggal = data.get("mulai"), data.get("selesai"), data.get("tanggal")
        if mulai and selesai and selesai <= mulai:
            self.add_error("selesai", "Jam selesai harus setelah jam mulai.")
        if mulai and selesai and tanggal:
            bentrok = SesiAnjangsana.objects.filter(tanggal=tanggal, mulai__lt=selesai, selesai__gt=mulai)
            if self.instance.pk:
                bentrok = bentrok.exclude(pk=self.instance.pk)
            if bentrok.exists():
                self.add_error("mulai", "Bertumpuk dengan sesi lain pada tanggal yang sama.")
        return data


@superadmin_wajib
def kelola(request):
    form = FormSesi()
    if request.method == "POST":
        aksi = request.POST.get("aksi")
        if aksi == "status":
            nilai = request.POST.get("paksa")
            if nilai in dict(StatusPaksa.PILIHAN):
                lama = pengaturan.ambil("anjangsana.paksa_status")
                pengaturan.simpan("anjangsana.paksa_status", nilai, oleh=request.user.username)
                catat(request, "anjangsana.status_diubah", lama={"paksa": lama}, baru={"paksa": nilai})
                messages.success(request, f"Status Anjangsana: {dict(StatusPaksa.PILIHAN)[nilai]}.")
            return redirect("anjangsana_admin:kelola")
        if aksi == "tambah":
            form = FormSesi(request.POST)
            if form.is_valid():
                s = form.save()
                catat(request, "anjangsana.sesi_ditambah", s, keterangan=str(s))
                messages.success(request, f"Sesi {s} ditambahkan.")
                return redirect("anjangsana_admin:kelola")
        if aksi in ("ubah", "hapus"):
            s = get_object_or_404(SesiAnjangsana, pk=request.POST.get("pk"))
            if aksi == "hapus":
                teks = str(s)
                s.delete()  # Kunjungan.sesi SET_NULL: data kunjungan tetap ada
                catat(request, "anjangsana.sesi_dihapus", keterangan=teks)
                messages.success(request, f"Sesi {teks} dihapus.")
                return redirect("anjangsana_admin:kelola")
            lama = str(s)
            f_ubah = FormSesi(request.POST, instance=s)
            if f_ubah.is_valid():
                f_ubah.save()
                catat(request, "anjangsana.sesi_diubah", s, keterangan=f"{lama} -> {s}")
                messages.success(request, f"Sesi diubah menjadi {s}.")
            else:
                for galat in f_ubah.errors.values():
                    messages.error(request, f"Sesi {lama} tidak diubah: {galat[0]}")
            return redirect("anjangsana_admin:kelola")
    return render(request, "anjangsana/kelola.html", {
        "menu_aktif": "anjangsana", "st": svc.status(), "sesi": SesiAnjangsana.objects.all(), "form": form,
        "pilihan_paksa": StatusPaksa.PILIHAN, "url_publik": url_anjangsana(),
        "jumlah_kunjungan": Kunjungan.objects.count(), "jumlah_review": Review.objects.count(),
    })  # fmt: skip


@superadmin_wajib
def poster(request):
    catat(request, "anjangsana.poster_diunduh")
    respons = HttpResponse(poster_pdf(), content_type="application/pdf")
    respons["Content-Disposition"] = 'inline; filename="poster-anjangsana.pdf"'
    return respons
