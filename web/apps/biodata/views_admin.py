"""Halaman superadmin untuk biodata: dasbor, daftar, detail, ubah, tambah, hapus, unduh."""

from __future__ import annotations

import io

import segno
from django import forms
from django.contrib import messages
from django.contrib.auth import authenticate
from django.core.paginator import Paginator
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.absensi.models import Kegiatan
from apps.akun.decorators import superadmin_wajib
from apps.inti import sampah as sampah_umum
from apps.inti.log import catat
from apps.inti.models import LogAktivitas, Tingkat
from apps.kartu.models import AlasanKartu, KartuRiwayat
from apps.kartu.services import data_terkunci
from apps.kontingen.models import URUTAN_TINGKAT, Kontingen

from . import ekspor, kueri, services
from . import foto as foto_mod
from . import nik as nik_mod
from .forms import BiodataForm
from .models import JenisPenanda, PenandaPeserta, Peran, Peserta, Sumber

TIPE_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _pelaku(request) -> str:
    return request.nama_pelaku or request.user.username


@superadmin_wajib
def dasbor(request):
    from apps.inti import pengaturan

    status = services.status_form(pengaturan.untuk_request(request))
    return render(
        request,
        "superadmin/dasbor.html",
        {
            "menu_aktif": "dasbor",
            "stat": kueri.statistik(),
            "kontingen": kueri.tabel_kontingen(),
            "status": status,
            "url_form": f"{request.build_absolute_uri('/daftar/')}",
        },
    )


@superadmin_wajib
def qr_form(request):
    """QR menuju link form biodata (PNG) untuk dibagikan panitia."""
    from django.conf import settings

    url = f"{settings.SIGAP_URL}/daftar/"
    buf = io.BytesIO()
    segno.make(url, error="q").save(buf, kind="png", scale=12, border=3, dark="#1F2937")
    respons = HttpResponse(buf.getvalue(), content_type="image/png")
    if request.GET.get("unduh"):
        respons["Content-Disposition"] = 'attachment; filename="QR_Form_Biodata_SIGAP_JUMBARA.png"'
    return respons


def _konteks_saringan(request):
    s = kueri.Saringan.dari_get(request.GET)
    return s, {
        "s": s,
        "pilihan_kontingen": Kontingen.objects.order_by(URUTAN_TINGKAT, "kode"),
        "pilihan_tingkat": Tingkat.choices,
        "pilihan_peran": Peran.choices,
        "pilihan_tanda": JenisPenanda.choices,
        "pilihan_kegiatan": Kegiatan.objects.filter(bisa_dipilih=True),
    }


@superadmin_wajib
def daftar(request):
    s, konteks = _konteks_saringan(request)
    qs = kueri.saring(s).prefetch_related("penanda")
    halaman = Paginator(qs, 50).get_page(request.GET.get("hal"))
    acuan = services.tanggal_acuan_usia()
    for p in halaman.object_list:
        p.umur = services.usia_pada(p.tanggal_lahir, acuan)
        p.tanda_aktif = [t for t in p.penanda.all() if t.diabaikan_pada is None]
    konteks.update({"menu_aktif": "biodata", "halaman": halaman, "jumlah": halaman.paginator.count})
    return render(request, "superadmin/biodata_daftar.html", konteks)


def _ambil(pk: int, termasuk_sampah: bool = False) -> Peserta:
    manager = Peserta.semua if termasuk_sampah else Peserta.objects
    return get_object_or_404(manager.select_related("kontingen"), pk=pk)


@superadmin_wajib
def detail(request, pk: int):
    p = _ambil(pk, termasuk_sampah=True)
    riwayat = LogAktivitas.objects.filter(subjek_tipe="peserta", subjek_id=str(p.pk)).order_by("-dibuat_pada")[:50]
    acuan = services.tanggal_acuan_usia()
    return render(
        request,
        "superadmin/biodata_detail.html",
        {
            "menu_aktif": "biodata",
            "p": p,
            "umur": services.usia_pada(p.tanggal_lahir, acuan),
            "tanda": p.penanda.all().order_by("diabaikan_pada", "jenis"),
            "riwayat": riwayat,
            "riwayat_kartu": KartuRiwayat.objects.filter(peserta=p).order_by("-dibuat_pada"),
            "pilihan_alasan": AlasanKartu.choices,
            "terkunci": data_terkunci(),
        },
    )


@superadmin_wajib
def foto(request, pk: int):
    p = _ambil(pk, termasuk_sampah=True)
    path = foto_mod.path_lengkap(p.foto_path)
    if path is None:
        raise Http404
    respons = FileResponse(open(path, "rb"), content_type="image/jpeg")
    respons["Cache-Control"] = "no-store, private"
    if request.GET.get("unduh"):
        respons["Content-Disposition"] = f'attachment; filename="{p.kode_pendaftaran}.jpg"'
    return respons


@superadmin_wajib
@require_POST
def lihat_nik(request, pk: int):
    p = _ambil(pk, termasuk_sampah=True)
    catat(request, "nik.dilihat", p, keterangan=f"NIK {p.kode_pendaftaran} dibuka")
    return JsonResponse({"nik": nik_mod.dekripsi(p.nik_terenkripsi)})


def _data_awal(p: Peserta) -> dict:
    return {
        "kontingen": p.kontingen_id,
        "tingkat": p.tingkat,
        "peran": p.peran,
        "nama_lengkap": p.nama_lengkap,
        "nik": nik_mod.dekripsi(p.nik_terenkripsi),
        "nomor_induk_anggota": p.nomor_induk_anggota,
        "jenis_kelamin": p.jenis_kelamin,
        "tempat_lahir": p.tempat_lahir,
        "tanggal_lahir": p.tanggal_lahir,
        "alamat": p.alamat,
        "golongan_darah": p.golongan_darah,
        "telepon": p.telepon,
        "nama_orang_tua": p.nama_orang_tua,
        "telepon_orang_tua": p.telepon_orang_tua,
        "kegiatan": list(p.kegiatan.all()),
    }


@superadmin_wajib
def ubah(request, pk: int):
    p = _ambil(pk)
    if request.method == "POST":
        form = BiodataForm(request.POST, request.FILES, mode="superadmin", peserta=p)
        if form.is_valid():
            try:
                services.ubah_peserta(request, p, form.cleaned_data, form.hasil_foto)
            except services.NikSudahTerdaftar:
                form.add_error("nik", "NIK ini sudah dipakai biodata lain.")
            else:
                messages.success(request, f"Biodata {p.nama_lengkap} ({p.kode_pendaftaran}) disimpan.")
                return redirect("biodata_admin:detail", pk=p.pk)
    else:
        form = BiodataForm(mode="superadmin", peserta=p, initial=_data_awal(p))
    return render(request, "superadmin/biodata_form.html", {"menu_aktif": "biodata", "form": form, "p": p})


@superadmin_wajib
def tambah(request):
    if request.method == "POST":
        form = BiodataForm(request.POST, request.FILES, mode="superadmin")
        if form.is_valid():
            try:
                p = services.buat_peserta(request, form.cleaned_data, form.hasil_foto, Sumber.SUPERADMIN)
            except services.NikSudahTerdaftar:
                form.add_error("nik", "NIK ini sudah terdaftar.")
            else:
                messages.success(request, f"Biodata {p.nama_lengkap} ditambahkan dengan kode {p.kode_pendaftaran}.")
                return redirect("biodata_admin:detail", pk=p.pk)
    else:
        form = BiodataForm(mode="superadmin")
    return render(request, "superadmin/biodata_form.html", {"menu_aktif": "tambah", "form": form, "p": None})


@superadmin_wajib
@require_POST
def hapus(request, pk: int):
    p = _ambil(pk)
    services.hapus_peserta(request, p)
    messages.success(request, f"Biodata {p.nama_lengkap} dipindah ke tempat sampah. Bisa dipulihkan.")
    return redirect("biodata_admin:daftar")


@superadmin_wajib
@require_POST
def abaikan_tanda(request, pk: int):
    t = get_object_or_404(PenandaPeserta.objects.select_related("peserta"), pk=pk)
    services.abaikan_tanda(request, t)
    messages.success(request, "Tanda ditandai sudah dicek.")
    return redirect("biodata_admin:detail", pk=t.peserta_id)


@superadmin_wajib
def sampah(request):
    return render(
        request,
        "superadmin/sampah.html",
        {
            "menu_aktif": "sampah",
            "peserta": Peserta.semua.filter(dihapus_pada__isnull=False)
            .select_related("kontingen")
            .order_by("-dihapus_pada"),
            "kontingen": Kontingen.semua.filter(dihapus_pada__isnull=False).order_by("-dihapus_pada"),
            "lainnya": sampah_umum.daftar(),
        },
    )


@superadmin_wajib
@require_POST
def sampah_aksi(request, jenis: str, pk: int, aksi: str):
    """Pulihkan / hapus permanen form, kiriman form, kehadiran, review Anjangsana."""
    try:
        if aksi == "pulihkan":
            label = sampah_umum.pulihkan(request, jenis, pk)
            messages.success(request, f"Dipulihkan: {label}.")
        elif aksi == "hapus-permanen":
            label = sampah_umum.hapus_permanen(request, jenis, pk)
            messages.success(request, f"Dihapus permanen: {label}.")
    except sampah_umum.GagalSampah as e:
        messages.error(request, e.pesan)
    return redirect(f"{reverse('biodata_admin:sampah')}#{jenis}")


@superadmin_wajib
@require_POST
def pulihkan(request, pk: int):
    p = get_object_or_404(Peserta.semua.filter(dihapus_pada__isnull=False), pk=pk)
    if p.kontingen.terhapus:
        messages.error(request, "Kontingen biodata ini ada di tempat sampah. Pulihkan kontingennya dulu.")
        return redirect("biodata_admin:sampah")
    try:
        services.pulihkan_peserta(request, p)
    except services.NikSudahTerdaftar:
        messages.error(
            request, f"Tidak bisa memulihkan {p.nama_lengkap}: NIK-nya sudah dipakai biodata lain yang aktif."
        )
    else:
        messages.success(request, f"Biodata {p.nama_lengkap} dipulihkan.")
    return redirect("biodata_admin:sampah")


@superadmin_wajib
@require_POST
def hapus_permanen(request, pk: int):
    p = get_object_or_404(Peserta.semua.filter(dihapus_pada__isnull=False), pk=pk)
    if request.POST.get("konfirmasi", "").strip().upper() != p.kode_pendaftaran:
        messages.error(request, f"Ketik kode {p.kode_pendaftaran} dengan benar untuk menghapus permanen.")
        return redirect("biodata_admin:sampah")
    if p.kehadiran.exists():
        messages.error(request, "Biodata ini sudah punya catatan kehadiran, jadi tidak bisa dihapus permanen.")
        return redirect("biodata_admin:sampah")
    nama = p.nama_lengkap
    services.hapus_permanen_peserta(request, p)
    messages.success(request, f"Biodata {nama} dihapus permanen.")
    return redirect("biodata_admin:sampah")


def _keterangan_saringan(s: kueri.Saringan) -> str:
    if not s.aktif:
        return "Tanpa saringan (semua biodata)."
    return "Saringan: " + ", ".join(f"{k}={getattr(s, k)}" for k in s.aktif)


@superadmin_wajib
def unduh_umum(request):
    s = kueri.Saringan.dari_get(request.GET)
    qs = kueri.saring(s)
    isi = ekspor.excel_biodata(qs, lengkap=False, keterangan_saringan=_keterangan_saringan(s))
    catat(request, "ekspor.umum", keterangan=f"Excel umum, {qs.count()} baris. {_keterangan_saringan(s)}"[:255])
    nama = f"Biodata_Jumbara_umum_{timezone.localtime():%Y%m%d_%H%M}.xlsx"
    respons = HttpResponse(isi, content_type=TIPE_XLSX)
    respons["Content-Disposition"] = f'attachment; filename="{nama}"'
    return respons


class FormKonfirmasiSandi(forms.Form):
    password = forms.CharField(
        label="Kata sandi superadmin",
        widget=forms.PasswordInput(attrs={"class": "input", "autocomplete": "current-password"}),
    )


@superadmin_wajib
def unduh_lengkap(request):
    """Excel berisi NIK utuh, alamat, kontak orang tua. Wajib konfirmasi ulang kata sandi."""
    s = kueri.Saringan.dari_get(request.GET)
    form = FormKonfirmasiSandi(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(request, username=request.user.username, password=form.cleaned_data["password"])
        if user is None or user.pk != request.user.pk:
            catat(request, "ekspor.lengkap_gagal", keterangan="Kata sandi salah saat unduh Excel lengkap")
            form.add_error("password", "Kata sandi salah.")
        else:
            qs = kueri.saring(s)
            isi = ekspor.excel_biodata(qs, lengkap=True, keterangan_saringan=_keterangan_saringan(s))
            catat(
                request,
                "ekspor.lengkap",
                keterangan=f"Excel LENGKAP, {qs.count()} baris. {_keterangan_saringan(s)}"[:255],
            )
            nama = f"Biodata_Jumbara_LENGKAP_RAHASIA_{timezone.localtime():%Y%m%d_%H%M}.xlsx"
            respons = HttpResponse(isi, content_type=TIPE_XLSX)
            respons["Content-Disposition"] = f'attachment; filename="{nama}"'
            return respons
    return render(
        request,
        "superadmin/unduh_lengkap.html",
        {"menu_aktif": "biodata", "form": form, "s": s, "jumlah": kueri.saring(s).count()},
    )


@superadmin_wajib
def unduh_foto(request):
    kontingen = get_object_or_404(Kontingen, pk=request.GET.get("kontingen") or 0)
    qs = Peserta.objects.filter(kontingen=kontingen).exclude(foto_path="").order_by("nama_lengkap")
    isi, jumlah = ekspor.zip_foto(qs)
    catat(request, "ekspor.foto", kontingen, keterangan=f"ZIP foto {kontingen.kode}, {jumlah} foto")
    respons = HttpResponse(isi, content_type="application/zip")
    respons["Content-Disposition"] = f'attachment; filename="Foto_{kontingen.kode}.zip"'
    return respons
