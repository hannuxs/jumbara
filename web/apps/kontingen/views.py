"""Superadmin: kelola kontingen dan kuota."""

from __future__ import annotations

from django import forms
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.akun.decorators import superadmin_wajib
from apps.biodata.kueri import ada_tanda_aktif, tabel_kontingen
from apps.biodata.models import Peran, Peserta
from apps.biodata.services import hitung_ulang_tanda_kontingen, tanggal_acuan_usia, usia_pada
from apps.inti import seed
from apps.inti.log import catat, selisih

from .models import Kontingen


class FormKontingen(forms.ModelForm):
    class Meta:
        model = Kontingen
        fields = ["kode", "nama", "tingkat", "kuota", "catatan"]
        labels = {
            "kode": "Kode",
            "nama": "Nama resmi sekolah",
            "tingkat": "Tingkat",
            "kuota": "Kuota orang",
            "catatan": "Catatan superadmin",
        }
        help_texts = {
            "kode": "Contoh: MA-18. Dipakai di kartu dan Excel.",
            "nama": "Nama ini tampil di pilihan form biodata, kartu, dan piagam.",
            "kuota": "Jumlah orang (peserta + pimpinan + pembina + peninjau). Form tidak pernah menolak karena kuota.",
        }
        widgets = {"catatan": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.setdefault("class", "input")

    def clean_kode(self) -> str:
        kode = self.cleaned_data["kode"].strip().upper()
        if Kontingen.objects.filter(kode=kode).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Kode ini sudah dipakai kontingen lain.")
        return kode

    def clean_nama(self) -> str:
        nama = " ".join(self.cleaned_data["nama"].split())
        if Kontingen.objects.filter(nama__iexact=nama).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Nama ini sudah dipakai kontingen lain.")
        return nama


def _data(k: Kontingen) -> dict:
    return {"kode": k.kode, "nama": k.nama, "tingkat": k.tingkat, "kuota": k.kuota, "catatan": k.catatan}


@superadmin_wajib
def daftar(request):
    return render(
        request,
        "superadmin/kontingen_daftar.html",
        {
            "menu_aktif": "kontingen",
            "baris": tabel_kontingen(),
            "dengan_catatan": Kontingen.objects.exclude(catatan_data=""),
        },
    )


@superadmin_wajib
def detail(request, pk: int):
    k = get_object_or_404(Kontingen, pk=pk)
    anggota = list(
        Peserta.objects.filter(kontingen=k).annotate(bertanda=ada_tanda_aktif())
        .order_by("peran", "nama_lengkap")
    )  # fmt: skip
    acuan = tanggal_acuan_usia()
    for p in anggota:
        p.umur = usia_pada(p.tanggal_lahir, acuan)
    urutan = {"PIMPINAN_KONTINGEN": 0, "PEMBINA_PENDAMPING": 1, "PESERTA": 2, "PENINJAU": 3}
    anggota.sort(key=lambda p: (urutan.get(p.peran, 9), p.nama_lengkap.lower()))
    hitung = dict(Peserta.objects.filter(kontingen=k).values_list("peran").annotate(n=Count("id")))
    per_peran = [(p.label, hitung.get(p.value, 0)) for p in Peran]
    return render(
        request,
        "superadmin/kontingen_detail.html",
        {"menu_aktif": "kontingen", "k": k, "anggota": anggota, "per_peran": per_peran},
    )


@superadmin_wajib
def tambah(request):
    form = FormKontingen(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            k = form.save(commit=False)
            k.kuota_awal = k.kuota
            k.kuota_diubah_manual = True
            k.save()
            catat(request, "kontingen.dibuat", k, keterangan=k.kode, baru=_data(k))
        messages.success(request, f"Kontingen {k.nama} ditambahkan dan langsung muncul di form biodata.")
        return redirect("kontingen_admin:daftar")
    return render(request, "superadmin/kontingen_form.html", {"menu_aktif": "kontingen", "form": form, "k": None})


@superadmin_wajib
def ubah(request, pk: int):
    k = get_object_or_404(Kontingen, pk=pk)
    lama = _data(k)
    kuota_lama = k.kuota
    form = FormKontingen(request.POST or None, instance=k)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            k = form.save(commit=False)
            if k.kuota != kuota_lama:
                k.kuota_diubah_manual = True
            k.save()
            d_lama, d_baru = selisih(lama, _data(k))
            if d_baru:
                aksi = "kontingen.kuota_diubah" if "kuota" in d_baru else "kontingen.diubah"
                catat(request, aksi, k, keterangan=k.kode, lama=d_lama, baru=d_baru)
            if k.kuota != kuota_lama:
                hitung_ulang_tanda_kontingen(k)
        messages.success(request, f"Kontingen {k.nama} disimpan.")
        return redirect("kontingen_admin:daftar")
    return render(request, "superadmin/kontingen_form.html", {"menu_aktif": "kontingen", "form": form, "k": k})


@superadmin_wajib
@require_POST
def hapus(request, pk: int):
    k = get_object_or_404(Kontingen, pk=pk)
    jumlah = Peserta.objects.filter(kontingen=k).count()
    if jumlah:
        messages.error(
            request, f"Kontingen {k.nama} masih punya {jumlah} biodata. Pindahkan atau hapus biodatanya dulu."
        )
        return redirect("kontingen_admin:daftar")
    k.hapus_lunak(oleh=request.nama_pelaku or request.user.username)
    catat(request, "kontingen.dihapus", k, keterangan=f"{k.kode} ke tempat sampah")
    messages.success(request, f"Kontingen {k.nama} dipindah ke tempat sampah.")
    return redirect("kontingen_admin:daftar")


@superadmin_wajib
@require_POST
def pulihkan(request, pk: int):
    k = get_object_or_404(Kontingen.semua.filter(dihapus_pada__isnull=False), pk=pk)
    if Kontingen.objects.filter(Q(kode=k.kode) | Q(nama__iexact=k.nama)).exists():
        messages.error(request, f"Tidak bisa memulihkan {k.nama}: kode atau namanya sudah dipakai kontingen aktif.")
    else:
        k.pulihkan()
        catat(request, "kontingen.dipulihkan", k, keterangan=k.kode)
        messages.success(request, f"Kontingen {k.nama} dipulihkan.")
    return redirect("biodata_admin:sampah")


@superadmin_wajib
@require_POST
def impor_ulang(request):
    """Impor ulang data/kontingen.csv: hanya menambah yang baru dan memperbarui kuota yang belum diubah manual."""
    laporan: list[str] = []
    with transaction.atomic():
        seed.seed_kontingen(seed.FOLDER_DATA, laporan)
        catat(request, "kontingen.impor_ulang", keterangan="; ".join(laporan)[:255])
    messages.success(request, "Impor ulang selesai. " + " ".join(laporan))
    return redirect("kontingen_admin:daftar")
