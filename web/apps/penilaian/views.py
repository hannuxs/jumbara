"""Mengisi form: juri (akun juri), superadmin, dan publik (link tanpa login, mode 1)."""

from __future__ import annotations

from urllib.parse import urlencode

from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django_ratelimit.core import is_ratelimited

from apps.akun.decorators import peran_wajib, superadmin_wajib

from . import hasil as hs
from . import services as svc
from .forms import FormIsian
from .models import AksesForm, Formulir, JenisSubjek, Kiriman, ModeForm, StatusForm

BATAS_PUBLIK = "20/10m"


def _label_nama(f: Formulir) -> str:
    return "Nama Juri" if f.penilaian else "Nama pengisi"


# --- Juri ----------------------------------------------------------------------------------------------------


@peran_wajib("JURI", "SUPERADMIN")
def juri_beranda(request):
    """Daftar form yang ditugaskan ke juri, dikelompokkan per kegiatan."""
    daftar = (
        Formulir.objects.filter(akses=AksesForm.JURI, status=StatusForm.AKTIF)
        .select_related("kegiatan")
        .order_by("kegiatan__urutan", "kegiatan__nama", "tingkat", "judul")
    )
    sekarang = timezone.now()
    grup: dict[str, list] = {}
    for f in daftar:
        nama = f.kegiatan.nama if f.kegiatan else "Lainnya"
        grup.setdefault(nama, []).append({"f": f, "terbuka": f.terbuka(sekarang)})
    return render(request, "penilaian/juri_beranda.html", {"grup": grup})


def _form_juri(request, slug: str) -> Formulir:
    f = get_object_or_404(Formulir, slug=slug)
    if not request.user.superadmin and (f.akses != AksesForm.JURI or f.status != StatusForm.AKTIF):
        raise Http404
    return f


@peran_wajib("JURI", "SUPERADMIN")
def juri_subjek(request, slug: str):
    """Pilih subjek; status sudah/belum dinilai oleh juri dengan nama ini (nama dari perangkat)."""
    f = _form_juri(request, slug)
    nama = " ".join((request.GET.get("nama") or getattr(request, "nama_pelaku", "") or "").split())
    sudah = {}
    if nama:
        for x in Kiriman.objects.filter(formulir=f):
            if x.nama_pengisi.casefold() == nama.casefold():
                sudah[x.kunci_subjek] = x
    subjek = [{"s": s, "kiriman": sudah.get(s.kunci)} for s in hs.daftar_subjek(f)]
    return render(request, "penilaian/juri_subjek.html", {
        "f": f, "subjek": subjek, "nama": nama, "terbuka": f.terbuka(), "n_sudah": len(sudah),
    })  # fmt: skip


@peran_wajib("JURI", "SUPERADMIN")
def juri_isi(request, slug: str, kunci: str):
    f = _form_juri(request, slug)
    return _isi(request, f, kunci, kembali=f"/juri/{f.slug}/", mode_juri=True)


@peran_wajib("JURI", "SUPERADMIN")
def juri_hasil(request, slug: str):
    f = _form_juri(request, slug)
    if not (f.juri_lihat_hasil or request.user.superadmin) or not f.penilaian:
        raise Http404
    tabel = hs.tabel_hasil(f)
    baris = sorted(tabel.baris, key=lambda b: (b.peringkat is None, b.peringkat or 0, b.subjek.label))
    kolom = [k for k in tabel.kolom if k.kode == f.kolom_urut]
    return render(request, "penilaian/juri_hasil.html", {"f": f, "baris": baris, "kolom": kolom})


# --- Superadmin ------------------------------------------------------------------------------------------------


@superadmin_wajib
def isi_admin(request, slug: str):
    f = get_object_or_404(Formulir, slug=slug)
    kunci = request.GET.get("subjek") or request.POST.get("subjek_kunci") or ""
    if f.jenis_subjek != JenisSubjek.BEBAS and not kunci:
        return render(request, "penilaian/pilih_subjek.html", {
            "f": f, "subjek": hs.daftar_subjek(f), "kembali": f"/superadmin/form/{f.pk}/",
        })  # fmt: skip
    return _isi(request, f, kunci, kembali=f"/superadmin/form/{f.pk}/hasil/")


# --- Publik -------------------------------------------------------------------------------------------------------


def isi_publik(request, slug: str):
    f = get_object_or_404(Formulir, slug=slug, akses=AksesForm.PUBLIK, mode=ModeForm.INPUT)
    if f.status != StatusForm.AKTIF:
        raise Http404
    if not f.terbuka():
        return render(request, "penilaian/tutup.html", {"f": f, "now": timezone.now()})
    if request.method == "POST" and is_ratelimited(
        request, group="form.publik", key="ip", rate=BATAS_PUBLIK, method="POST", increment=True
    ):
        messages.error(request, "Terlalu banyak kiriman dari jaringan ini. Tunggu beberapa menit lalu coba lagi.")
        return redirect("penilaian:isi_publik", slug=f.slug)
    kunci = request.POST.get("subjek_kunci") or request.GET.get("subjek") or ""
    return _isi(request, f, kunci, kembali="", publik=True)


def terkirim(request, slug: str):
    f = get_object_or_404(Formulir, slug=slug)
    return render(request, "penilaian/terkirim.html", {"f": f, "lagi": request.GET.get("lagi", "")})


# --- Bersama ---------------------------------------------------------------------------------------------------------


def _isi(request, f: Formulir, kunci: str, kembali: str, mode_juri: bool = False, publik: bool = False):
    kolom = list(f.kolom.all())
    subjek = None
    daftar = hs.daftar_subjek(f) if (publik and f.jenis_subjek == JenisSubjek.KONTINGEN) else None
    if f.jenis_subjek != JenisSubjek.BEBAS and kunci:
        subjek = hs.subjek_dari_kunci(f, kunci)
        if subjek is None:
            raise Http404
    nama_awal = getattr(request, "nama_pelaku", "") if not publik else ""
    form = FormIsian(
        kolom, request.POST or None, request.FILES or None, label_nama=_label_nama(f),
        initial={"nama_pengisi": request.GET.get("nama") or nama_awal},
    )  # fmt: skip
    sudah = []
    if subjek and f.penilaian and not publik:
        nama = request.POST.get("nama_pengisi") or request.GET.get("nama") or nama_awal
        sudah = svc.kiriman_juri(f, subjek, nama) if nama else []
    galat = ""
    if request.method == "POST":
        if f.jenis_subjek != JenisSubjek.BEBAS and subjek is None:
            galat = (
                "Pilih " + ("kontingen" if f.jenis_subjek == JenisSubjek.KONTINGEN else "orang") + " terlebih dahulu."
            )
        elif form.is_valid():
            data, berkas = form.data_bersih()
            try:
                x, diganti = svc.kirim(
                    request, f, data, berkas, form.cleaned_data["nama_pengisi"], subjek,
                    client_uuid=request.POST.get("client_uuid"),
                )  # fmt: skip
            except svc.GagalForm as e:
                galat = e.pesan
            else:
                if publik:
                    return redirect("penilaian:terkirim", slug=f.slug)
                messages.success(
                    request,
                    ("Nilai diperbarui" if diganti else "Nilai terkirim")
                    + (f" untuk {subjek.label}." if subjek else "."),
                )
                nama = form.cleaned_data["nama_pengisi"]
                if mode_juri:
                    return redirect(f"/juri/{f.slug}/?{urlencode({'nama': nama})}")
                return redirect(kembali or f"/superadmin/form/{f.pk}/hasil/")
        else:
            galat = "Ada isian yang perlu diperbaiki."
    return render(request, "penilaian/isi.html", {
        "f": f, "form": form, "subjek_terpilih": subjek, "daftar_subjek": daftar, "kembali": kembali, "galat": galat,
        "publik": publik, "mode_juri": mode_juri, "sudah": sudah, "terbuka": f.terbuka() or request.user.is_authenticated and request.user.superadmin,
        "kunci_draf": f"sigap-draf-{f.slug}-{getattr(subjek, 'kunci', 'bebas')}",
    })  # fmt: skip
