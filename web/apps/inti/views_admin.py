"""Superadmin: pengaturan form, log aktivitas, cadangan data."""

from __future__ import annotations

import contextlib
import io
from datetime import date, datetime

import xlsxwriter
from django import forms
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.akun.decorators import superadmin_wajib
from apps.biodata.services import normalisasi_telepon

from . import cadangan, pengaturan
from .log import catat, selisih
from .models import LogAktivitas
from .pengaturan import StatusPaksa


class FormPengaturan(forms.Form):
    paksa_status = forms.ChoiceField(label="Status form biodata", choices=StatusPaksa.PILIHAN, widget=forms.RadioSelect)
    buka_pada = forms.DateTimeField(
        label="Dibuka pada (WITA)",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
    )
    tutup_pada = forms.DateTimeField(
        label="Ditutup pada (WITA)",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
    )
    foto_wajib = forms.BooleanField(label="Foto wajib diunggah", required=False)
    kontak_nama = forms.CharField(
        label="Nama kontak superadmin",
        max_length=60,
        help_text="Tampil di halaman publik, misalnya “Kak Farhan (Superadmin)”.",
    )
    kontak_wa = forms.CharField(
        label="Nomor WhatsApp superadmin",
        max_length=20,
        required=False,
        help_text="Contoh: 081234567890. Dipakai tombol WhatsApp di halaman publik.",
    )
    pengumuman = forms.CharField(
        label="Pengumuman di beranda dan form", required=False, max_length=500, widget=forms.Textarea(attrs={"rows": 3})
    )
    waktu_minimal_detik = forms.IntegerField(
        label="Waktu minimal pengisian (detik)",
        min_value=0,
        max_value=120,
        help_text="Kiriman lebih cepat dari ini dianggap robot. Bawaan 10.",
    )
    tanggal_acuan_usia = forms.DateField(
        label="Tanggal acuan hitung usia", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
    )
    perawatan = forms.BooleanField(
        label="Mode perawatan (semua halaman ditutup kecuali untuk superadmin)", required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for _nama, f in self.fields.items():
            if not isinstance(f.widget, forms.RadioSelect | forms.CheckboxInput):
                f.widget.attrs.setdefault("class", "input")

    def clean_kontak_wa(self) -> str:
        teks = self.cleaned_data.get("kontak_wa", "").strip()
        if not teks:
            return ""
        nomor = normalisasi_telepon(teks)
        if nomor is None:
            raise forms.ValidationError("Nomor WhatsApp tidak valid. Contoh: 081234567890.")
        return nomor

    def clean(self):
        data = super().clean()
        if data.get("buka_pada") and data.get("tutup_pada") and data["tutup_pada"] <= data["buka_pada"]:
            self.add_error("tutup_pada", "Waktu tutup harus setelah waktu buka.")
        return data


PETA = {
    "paksa_status": "biodata.paksa_status",
    "buka_pada": "biodata.buka_pada",
    "tutup_pada": "biodata.tutup_pada",
    "foto_wajib": "biodata.foto_wajib",
    "kontak_nama": "kontak.superadmin_nama",
    "kontak_wa": "kontak.superadmin_wa",
    "pengumuman": "pengumuman.teks",
    "waktu_minimal_detik": "biodata.waktu_minimal_detik",
    "tanggal_acuan_usia": "acara.tanggal_acuan_usia",
    "perawatan": "sistem.perawatan",
}


def _ke_json(nilai):
    if isinstance(nilai, datetime):
        return timezone.localtime(nilai).isoformat()
    if isinstance(nilai, date):
        return nilai.isoformat()
    return nilai


@superadmin_wajib
def pengaturan_form(request):
    nilai = pengaturan.semua()
    awal = {}
    for isian, kunci in PETA.items():
        v = nilai.get(kunci)
        if isian in ("buka_pada", "tutup_pada"):
            v = pengaturan.ke_datetime(v)
            v = timezone.localtime(v) if v else None
        elif isian == "tanggal_acuan_usia" and v:
            v = date.fromisoformat(v)
        awal[isian] = v
    form = FormPengaturan(request.POST or None, initial=awal)
    if request.method == "POST" and form.is_valid():
        lama = {k: _ke_json(awal[k]) for k in PETA}
        baru = {k: _ke_json(form.cleaned_data[k]) for k in PETA}
        d_lama, d_baru = selisih(lama, baru)
        oleh = request.nama_pelaku or request.user.username
        for isian in d_baru:
            pengaturan.simpan(PETA[isian], baru[isian], oleh)
        if d_baru:
            catat(request, "pengaturan.diubah", keterangan=", ".join(d_baru), lama=d_lama, baru=d_baru)
            messages.success(request, "Pengaturan disimpan.")
        else:
            messages.info(request, "Tidak ada yang berubah.")
        return redirect("inti_admin:pengaturan")
    from apps.biodata.services import status_form

    return render(
        request, "superadmin/pengaturan.html", {"menu_aktif": "pengaturan", "form": form, "status": status_form(nilai)}
    )


def _saring_log(get):
    qs = LogAktivitas.objects.select_related("pengguna")
    if get.get("aksi"):
        qs = qs.filter(aksi=get["aksi"])
    if get.get("peran"):
        qs = qs.filter(peran=get["peran"])
    if get.get("nama"):
        qs = qs.filter(nama_pelaku__icontains=get["nama"])
    if get.get("subjek_tipe"):
        qs = qs.filter(subjek_tipe=get["subjek_tipe"])
    if get.get("subjek_id"):
        qs = qs.filter(subjek_id=get["subjek_id"])
    if get.get("q"):
        qs = qs.filter(keterangan__icontains=get["q"])
    for nama, lookup in (("dari", "dibuat_pada__date__gte"), ("sampai", "dibuat_pada__date__lte")):
        with contextlib.suppress(ValueError):
            qs = qs.filter(**{lookup: date.fromisoformat(get.get(nama, ""))})
    return qs.order_by("-dibuat_pada", "-id")


@superadmin_wajib
def log_daftar(request):
    qs = _saring_log(request.GET)
    halaman = Paginator(qs, 100).get_page(request.GET.get("hal"))
    return render(
        request,
        "superadmin/log.html",
        {
            "menu_aktif": "log",
            "halaman": halaman,
            "daftar_aksi": LogAktivitas.objects.order_by("aksi").values_list("aksi", flat=True).distinct(),
            "g": request.GET,
        },
    )


@superadmin_wajib
def log_unduh(request):
    qs = _saring_log(request.GET)[:50000]
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True, "remove_timezone": True})
    ws = wb.add_worksheet("Log")
    kepala = wb.add_format({"bold": True, "bg_color": "#FFF3E4"})
    waktu = wb.add_format({"num_format": "dd/mm/yyyy hh:mm:ss"})
    judul = [
        "Waktu",
        "Akun",
        "Peran",
        "Nama pelaku",
        "Aksi",
        "Subjek",
        "ID",
        "Keterangan",
        "Data lama",
        "Data baru",
        "IP",
        "Perangkat",
    ]
    ws.write_row(0, 0, judul, kepala)
    for r, x in enumerate(qs, start=1):
        ws.write_datetime(r, 0, timezone.localtime(x.dibuat_pada).replace(tzinfo=None), waktu)
        ws.write_row(r, 1, [x.pengguna.username if x.pengguna else "", x.peran, x.nama_pelaku, x.aksi, x.subjek_tipe,
                            x.subjek_id, x.keterangan, str(x.data_lama or ""), str(x.data_baru or ""), x.ip or "", x.perangkat_id])  # fmt: skip
    ws.set_column(0, 0, 18)
    ws.set_column(1, 6, 13)
    ws.set_column(7, 9, 40)
    ws.freeze_panes(1, 0)
    wb.close()
    catat(request, "ekspor.log", keterangan="Unduh log aktivitas")
    respons = HttpResponse(
        buf.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    respons["Content-Disposition"] = f'attachment; filename="Log_SIGAP_{timezone.localtime():%Y%m%d_%H%M}.xlsx"'
    return respons


@superadmin_wajib
def cadangan_daftar(request):
    nilai = pengaturan.semua()
    return render(
        request,
        "superadmin/cadangan.html",
        {
            "menu_aktif": "cadangan",
            "daftar": cadangan.daftar(),
            "folder": cadangan.folder(),
            "terakhir": pengaturan.ke_datetime(nilai.get("jadwal.cadangan_terakhir")),
        },
    )


@superadmin_wajib
@require_POST
def cadangan_buat(request):
    try:
        info = cadangan.buat("manual")
    except cadangan.GagalCadangan as e:
        catat(request, "cadangan.gagal", keterangan=str(e)[:255])
        messages.error(request, f"Cadangan gagal: {e}")
    else:
        pengaturan.simpan("jadwal.cadangan_terakhir", timezone.localtime().isoformat(), request.user.username)
        catat(request, "cadangan.dibuat", keterangan=f"{info.nama} ({info.ukuran // 1024} KB, manual)")
        messages.success(request, f"Cadangan dibuat: {info.nama}")
    return redirect("inti_admin:cadangan")


@superadmin_wajib
def cadangan_unduh(request, nama: str):
    path = cadangan.path_aman(nama)
    if path is None:
        raise Http404
    catat(request, "cadangan.diunduh", keterangan=nama)
    return FileResponse(open(path, "rb"), as_attachment=True, filename=nama)
