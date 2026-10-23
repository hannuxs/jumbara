"""Halaman superadmin piagam (docs/18-PIAGAM.md)."""

from __future__ import annotations

import io
import json
import re
import zipfile

from django import forms
from django.contrib import messages
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from apps.akun.decorators import superadmin_wajib
from apps.biodata.models import Peserta
from apps.inti import pengaturan
from apps.inti.log import catat
from apps.kontingen.models import Kontingen

from . import pdf as pdf_mod
from . import services as svc
from .models import JenisPiagam, PiagamTerbit, TemplatePiagam

KUNCI_PENGATURAN = {
    "format_nomor_peserta": "piagam.format_nomor_peserta",
    "format_nomor_juara": "piagam.format_nomor_juara",
    "digit_urut": "piagam.digit_urut",
    "tempat": "piagam.tempat",
    "tanggal": "piagam.tanggal",
    "syarat_daftar_ulang": "piagam.syarat_daftar_ulang",
}


def _pdf(isi: bytes, nama: str, unduh: bool = True) -> HttpResponse:
    r = HttpResponse(isi, content_type="application/pdf")
    r["Content-Disposition"] = f'{"attachment" if unduh else "inline"}; filename="{nama}"'
    return r


def _nama_file(teks: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", slugify(teks) or "piagam")[:80]


# --- Beranda dan pengaturan ---------------------------------------------------------------------------------


class FormPengaturan(forms.Form):
    format_nomor_peserta = forms.CharField(label="Format nomor piagam peserta", max_length=120)
    format_nomor_juara = forms.CharField(label="Format nomor piagam juara", max_length=120)
    digit_urut = forms.IntegerField(label="Jumlah digit nomor urut", min_value=1, max_value=6)
    tempat = forms.CharField(label="Tempat penerbitan", max_length=80)
    tanggal = forms.DateField(label="Tanggal piagam", widget=forms.DateInput(attrs={"type": "date"}))
    syarat_daftar_ulang = forms.BooleanField(label="Hanya yang sudah daftar ulang", required=False)

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        for f in self.fields.values():
            if not isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs.setdefault("class", "input")

    def clean(self):
        data = super().clean()
        for k in ("format_nomor_peserta", "format_nomor_juara"):
            if data.get(k) and "{urut}" not in data[k]:
                self.add_error(k, "Harus memuat {urut}, misalnya {urut}/PST/JUMBARA-V/2026.")
        return data


@superadmin_wajib
def beranda(request):
    svc.pastikan_template_bawaan()
    nilai = {k: pengaturan.ambil(v) for k, v in KUNCI_PENGATURAN.items()}
    form = FormPengaturan(request.POST or None, initial=nilai)
    if request.method == "POST" and form.is_valid():
        if PiagamTerbit.objects.exists() and any(
            form.cleaned_data[k] != nilai[k] for k in ("format_nomor_peserta", "format_nomor_juara", "digit_urut")
        ):
            messages.warning(request, "Format nomor diubah. Piagam yang sudah terbit tetap memakai nomor lamanya.")
        for k, v in KUNCI_PENGATURAN.items():
            baru = form.cleaned_data[k]
            pengaturan.simpan(v, baru.isoformat() if k == "tanggal" else baru, oleh=request.user.username)
        catat(request, "piagam.pengaturan_diubah", keterangan=json.dumps(form.cleaned_data, default=str)[:255])
        messages.success(request, "Pengaturan piagam disimpan.")
        return redirect("piagam_admin:beranda")
    du = svc.sudah_daftar_ulang_ids()
    syarat = pengaturan.ambil("piagam.syarat_daftar_ulang")
    terbit = dict(
        PiagamTerbit.objects.filter(jenis=JenisPiagam.PESERTA)
        .values_list("kontingen_id")
        .annotate(n=Count("id"))
        .order_by()
    )
    kontingen = []
    for k in Kontingen.objects.annotate(n=Count("peserta", filter=Q(peserta__dihapus_pada__isnull=True))).order_by(
        "kode"
    ):
        ids = list(Peserta.objects.filter(kontingen=k).values_list("pk", "tidak_berhak_piagam"))
        berhak = sum(1 for pk, tb in ids if not tb and (not syarat or pk in du))
        kontingen.append({"k": k, "jumlah": len(ids), "berhak": berhak, "terbit": terbit.get(k.pk, 0)})
    juara = (
        PiagamTerbit.objects.filter(jenis=JenisPiagam.JUARA)
        .values("sumber").annotate(n=Count("id")).order_by("sumber")
    )  # fmt: skip
    return render(request, "piagam/beranda.html", {
        "menu_aktif": "piagam", "form": form, "kontingen": kontingen, "template": TemplatePiagam.objects.all(),
        "juara": [{"sumber": j["sumber"], "n": j["n"], "judul": _judul_sumber(j["sumber"])} for j in juara],
        "total_berhak": sum(x["berhak"] for x in kontingen), "total": sum(x["jumlah"] for x in kontingen),
        "contoh_peserta": svc.nomor_dari_format(JenisPiagam.PESERTA, 1),
        "contoh_juara": svc.nomor_dari_format(JenisPiagam.JUARA, 1),
    })  # fmt: skip


def _judul_sumber(sumber: str) -> str:
    from apps.penilaian.models import Formulir

    if sumber.startswith("form:"):
        f = Formulir.semua.filter(pk=sumber.split(":", 1)[1]).first()
        return f.judul if f else sumber
    if sumber.startswith("anjangsana:"):
        t = sumber.split(":", 1)[1]
        return "Anjangsana" + ("" if t == "SEMUA" else f" - {t.title()}")
    return sumber


# --- Peserta per kontingen ---------------------------------------------------------------------------------------


@superadmin_wajib
def kontingen(request, pk: int):
    k = get_object_or_404(Kontingen, pk=pk)
    if request.method == "POST":
        p = get_object_or_404(Peserta, pk=request.POST.get("peserta"), kontingen=k)
        berhak = request.POST.get("berhak") == "1"
        alasan = request.POST.get("alasan", "")
        if not berhak and not alasan.strip():
            messages.error(request, "Isi alasan tidak berhak (misalnya sanksi menurut pedoman BAB VI D).")
        else:
            svc.atur_berhak(request, p, berhak, alasan)
            messages.success(request, f"{p.nama_lengkap}: {'berhak' if berhak else 'tidak berhak'} menerima piagam.")
        return redirect("piagam_admin:kontingen", pk=k.pk)
    return render(request, "piagam/kontingen.html", {
        "menu_aktif": "piagam", "k": k, "daftar": svc.daftar_peserta(k),
        "template": TemplatePiagam.objects.filter(jenis=JenisPiagam.PESERTA, aktif=True),
    })  # fmt: skip


@superadmin_wajib
def pengecualian(request):
    du = svc.sudah_daftar_ulang_ids()
    daftar = []
    for p in Peserta.objects.select_related("kontingen").order_by("kontingen__kode", "nama_lengkap"):
        alasan = svc.alasan_tidak_berhak(p, du)
        if alasan:
            daftar.append({"p": p, "alasan": alasan})
    return render(request, "piagam/pengecualian.html", {"menu_aktif": "piagam", "daftar": daftar})


def _template_dari(request, jenis: str) -> TemplatePiagam:
    pk = request.POST.get("template") or request.GET.get("template")
    return svc.template_aktif(jenis, int(pk) if pk and str(pk).isdigit() else None)


@superadmin_wajib
def unduh_peserta(request, pk: int):
    p = get_object_or_404(Peserta, pk=pk)
    try:
        hasil, lewat = svc.terbitkan_peserta(request, [p], _template_dari(request, JenisPiagam.PESERTA))
    except svc.GagalPiagam as e:
        messages.error(request, e.pesan)
        return redirect("piagam_admin:kontingen", pk=p.kontingen_id)
    if not hasil:
        messages.error(request, f"{p.nama_lengkap} tidak menerima piagam: {lewat[0][1]}.")
        return redirect("piagam_admin:kontingen", pk=p.kontingen_id)
    catat(request, "piagam.diunduh", p, keterangan=hasil[0].nomor)
    return _pdf(svc.pdf_terbit(hasil, f"Piagam {p.nama_lengkap}"), f"Piagam_{_nama_file(p.nama_lengkap)}.pdf")


@superadmin_wajib
def unduh_kontingen(request, pk: int):
    k = get_object_or_404(Kontingen, pk=pk)
    try:
        hasil, lewat = svc.terbitkan_peserta(
            request, list(Peserta.objects.filter(kontingen=k)), _template_dari(request, JenisPiagam.PESERTA)
        )
    except svc.GagalPiagam as e:
        messages.error(request, e.pesan)
        return redirect("piagam_admin:beranda")
    if not hasil:
        messages.error(request, f"Belum ada piagam yang bisa diterbitkan untuk {k.nama} ({len(lewat)} orang dilewati).")
        return redirect("piagam_admin:kontingen", pk=k.pk)
    catat(request, "piagam.diunduh", k, keterangan=f"{k.kode}: {len(hasil)} piagam, {len(lewat)} dilewati")
    return _pdf(svc.pdf_terbit(hasil, f"Piagam {k.nama}"), f"Piagam_{k.kode}_{_nama_file(k.nama)}.pdf")


@superadmin_wajib
def unduh_semua(request):
    try:
        template = _template_dari(request, JenisPiagam.PESERTA)
    except svc.GagalPiagam as e:
        messages.error(request, e.pesan)
        return redirect("piagam_admin:beranda")
    buf = io.BytesIO()
    total = dilewati = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for k in Kontingen.objects.order_by("kode"):
            hasil, lewat = svc.terbitkan_peserta(request, list(Peserta.objects.filter(kontingen=k)), template)
            dilewati += len(lewat)
            if hasil:
                total += len(hasil)
                z.writestr(f"Piagam_{k.kode}_{_nama_file(k.nama)}.pdf", svc.pdf_terbit(hasil, f"Piagam {k.nama}"))
    catat(request, "piagam.diunduh", keterangan=f"Semua kontingen: {total} piagam, {dilewati} dilewati")
    r = HttpResponse(buf.getvalue(), content_type="application/zip")
    r["Content-Disposition"] = f'attachment; filename="Piagam_Peserta_Semua_{svc.waktu()}.zip"'
    return r


@superadmin_wajib
def unduh_terbit(request, pk: int):
    x = get_object_or_404(PiagamTerbit, pk=pk)
    catat(request, "piagam.diunduh", x, keterangan=x.nomor)
    return _pdf(svc.pdf_terbit([x], x.nomor), f"Piagam_{_nama_file(x.nomor)}.pdf")


# --- Juara -------------------------------------------------------------------------------------------------------


def kegiatan_dari_form(f) -> str:
    if f.kegiatan_id:
        teks = f.kegiatan.nama
        return f"{teks} - {f.cabang}" if f.cabang else teks
    judul = re.sub(r"^(Penilaian|Hasil)\s+", "", f.judul)
    return re.sub(r"\s*-\s*(Mula|Madya|Wira)$", "", judul)


@superadmin_wajib
@require_POST
def juara_form(request, pk: int):
    from apps.penilaian.hasil import tabel_hasil
    from apps.penilaian.models import Formulir

    f = get_object_or_404(Formulir, pk=pk, mode="PENILAIAN")
    try:
        maks = max(1, min(10, int(request.POST.get("maks") or 3)))
        template = _template_dari(request, JenisPiagam.JUARA)
    except (ValueError, svc.GagalPiagam) as e:
        messages.error(request, getattr(e, "pesan", "Jumlah juara tidak valid."))
        return redirect(f"/superadmin/form/{f.pk}/hasil/")
    tabel = tabel_hasil(f)
    seri = [b for b in tabel.baris if b.peringkat and b.peringkat <= maks and b.seri]
    if seri and request.POST.get("abaikan_seri") != "1":
        messages.error(
            request,
            f'Ada {len(seri)} subjek seri di peringkat 1-{maks}. Isi pemecah seri dulu, atau centang "tetap terbitkan meski seri".',
        )
        return redirect(f"/superadmin/form/{f.pk}/hasil/")
    baris = [{"peringkat": b.peringkat, "tingkat": "" if b.subjek.tingkat == "SEMUA" or f.tingkat == "SEMUA" else b.subjek.tingkat.title(),
              "kontingen": b.subjek.kontingen, "peserta": b.subjek.peserta}
             for b in tabel.baris if b.peringkat and b.peringkat <= maks]  # fmt: skip
    if not baris:
        messages.error(request, "Belum ada subjek berperingkat. Periksa kolom peringkat dan nilai.")
        return redirect(f"/superadmin/form/{f.pk}/hasil/")
    kegiatan = " ".join((request.POST.get("kegiatan") or kegiatan_dari_form(f)).split())[:150]
    hasil = svc.terbitkan_juara(request, f"form:{f.pk}", baris, template, kegiatan)
    catat(request, "piagam.juara_diunduh", f, keterangan=f"{f.slug}: {len(hasil)} piagam juara 1-{maks}")
    return _pdf(svc.pdf_terbit(hasil, f"Piagam juara {f.judul}"), f"Piagam_Juara_{_nama_file(f.slug)}.pdf")


@superadmin_wajib
@require_POST
def juara_anjangsana(request):
    from apps.anjangsana.services import peringkat

    tingkat = request.POST.get("tingkat", "")
    if tingkat not in ("MULA", "MADYA", "WIRA", "SEMUA"):
        raise Http404
    try:
        maks = max(1, min(10, int(request.POST.get("maks") or 3)))
        template = _template_dari(request, JenisPiagam.JUARA)
    except (ValueError, svc.GagalPiagam) as e:
        messages.error(request, getattr(e, "pesan", "Jumlah juara tidak valid."))
        return redirect("/rekap/anjangsana/")
    data = [
        h for h in peringkat(None if tingkat == "SEMUA" else tingkat) if h["jumlah_review"] and h["peringkat"] <= maks
    ]
    if not data:
        messages.error(request, "Belum ada kontingen yang mendapat review Anjangsana.")
        return redirect("/rekap/anjangsana/")
    baris = [{"peringkat": h["peringkat"], "tingkat": "" if tingkat == "SEMUA" else tingkat.title(), "kontingen": h["k"],
              "peserta": None} for h in data]  # fmt: skip
    hasil = svc.terbitkan_juara(request, f"anjangsana:{tingkat}", baris, template, "Anjangsana")
    catat(request, "piagam.juara_diunduh", keterangan=f"Anjangsana {tingkat}: {len(hasil)} piagam")
    return _pdf(svc.pdf_terbit(hasil, "Piagam juara Anjangsana"), f"Piagam_Juara_Anjangsana_{tingkat}.pdf")


@superadmin_wajib
def juara_sumber(request, sumber: str):
    daftar = list(PiagamTerbit.objects.filter(jenis=JenisPiagam.JUARA, sumber=sumber).select_related("template"))
    if not daftar:
        raise Http404
    catat(request, "piagam.juara_diunduh", keterangan=f"{sumber}: {len(daftar)} piagam (unduh ulang)")
    return _pdf(svc.pdf_terbit(daftar, _judul_sumber(sumber)), f"Piagam_Juara_{_nama_file(_judul_sumber(sumber))}.pdf")


# --- Template -------------------------------------------------------------------------------------------------------


class AngkaMm(forms.FloatField):
    """Angka mm yang menerima koma atau titik; ditampilkan tanpa format lokal."""

    def __init__(self, *a, **kw):
        kw["widget"] = forms.TextInput(attrs={"inputmode": "decimal"})
        super().__init__(*a, **kw)

    def to_python(self, value):
        return super().to_python(str(value).strip().replace(",", ".") if value not in (None, "") else value)

    def prepare_value(self, value):
        return f"{value:g}" if isinstance(value, float) else value


class FormTemplate(forms.ModelForm):
    class Meta:
        model = TemplatePiagam
        fields = [
            "nama",
            "jenis",
            "ukuran_kertas",
            "orientasi",
            "desain_bawaan",
            "tempel_logo",
            "logo_x",
            "logo_y",
            "logo_tinggi",
            "aktif",
        ]
        field_classes = {"logo_x": AngkaMm, "logo_y": AngkaMm, "logo_tinggi": AngkaMm}
        labels = {
            "nama": "Nama template", "ukuran_kertas": "Ukuran kertas", "desain_bawaan": "Pakai bingkai bawaan SIGAP (bila tanpa latar)",
            "tempel_logo": "Tempel logo PMI + Jumbara V", "logo_x": "Logo: jarak dari kiri (mm, 0 = tengah)",
            "logo_y": "Logo: jarak dari atas (mm)", "logo_tinggi": "Logo: tinggi (mm)", "aktif": "Aktif (bisa dipilih saat menerbitkan)",
        }  # fmt: skip

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        for f in self.fields.values():
            if not isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs.setdefault("class", "input")


def _angka(e: dict, k: str, a: float, b: float, bawaan: float) -> float:
    try:
        v = float(e.get(k, bawaan))
    except (TypeError, ValueError):
        raise svc.GagalPiagam(f"Isian {k} harus angka.") from None
    return max(a, min(b, v))


def bersihkan_elemen(daftar) -> list[dict]:
    """Validasi elemen dari browser (jangan percaya browser)."""
    if not isinstance(daftar, list) or len(daftar) > 40:
        raise svc.GagalPiagam("Daftar elemen tidak valid (maksimal 40).")
    hasil = []
    for e in daftar:
        if not isinstance(e, dict):
            raise svc.GagalPiagam("Elemen tidak valid.")

        ukuran = _angka(e, "ukuran", 4, 96, 14)
        hasil.append({
            "kode": slugify(str(e.get("kode") or "teks"))[:30] or "teks",
            "teks": str(e.get("teks") or "")[:300],
            "x": round(_angka(e, "x", -50, 400, 20), 1), "y": round(_angka(e, "y", 0, 400, 50), 1),
            "lebar": round(_angka(e, "lebar", 5, 400, 200), 1), "ukuran": ukuran,
            "ukuran_min": min(ukuran, _angka(e, "ukuran_min", 4, 96, ukuran * 0.6)),
            "font": e.get("font") if e.get("font") in pdf_mod.HURUF else "INTER",
            "warna": e.get("warna") if re.fullmatch(r"#[0-9A-Fa-f]{6}", str(e.get("warna") or "")) else "#1F2937",
            "rata": e.get("rata") if e.get("rata") in pdf_mod.RATA else "TENGAH",
            "baris_maks": int(_angka(e, "baris_maks", 1, 6, 1)), "kapital": bool(e.get("kapital")),
        })  # fmt: skip
    return hasil


@superadmin_wajib
def template(request, pk: int | None = None):
    t = get_object_or_404(TemplatePiagam, pk=pk) if pk else None
    form = FormTemplate(request.POST or None, instance=t, prefix="t")
    if request.method == "POST" and request.POST.get("aksi") == "pengaturan" and form.is_valid():
        baru = t is None
        t = form.save(commit=False)
        if baru:
            t.elemen = svc.elemen_bawaan(t.jenis)
        t.save()
        catat(request, "piagam.template_disimpan", t, keterangan=t.nama)
        messages.success(request, "Template disimpan.")
        return redirect("piagam_admin:template", pk=t.pk)
    if t and request.method == "POST" and request.POST.get("aksi") == "latar":
        if request.FILES.get("latar"):
            try:
                svc.simpan_latar(request, t, request.FILES["latar"])
                messages.success(
                    request, "Latar diunggah. Atur posisi teks di pratinjau; matikan logo bila sudah ada di latar."
                )
            except svc.GagalPiagam as e:
                messages.error(request, e.pesan)
        elif request.POST.get("hapus_latar") == "1":
            t.latar, t.latar_asli, t.desain_bawaan = "", "", True
            t.save(update_fields=["latar", "latar_asli", "desain_bawaan", "diubah_pada"])
            catat(request, "piagam.latar_dihapus", t, keterangan=t.nama)
            messages.success(request, "Latar dihapus; kembali ke desain bawaan.")
        return redirect("piagam_admin:template", pk=t.pk)
    if t and request.method == "POST" and request.POST.get("aksi") == "elemen_bawaan":
        t.elemen = svc.elemen_bawaan(t.jenis)
        t.save(update_fields=["elemen", "diubah_pada"])
        catat(request, "piagam.template_disimpan", t, keterangan=f"{t.nama}: elemen dikembalikan ke bawaan")
        messages.success(request, "Elemen teks dikembalikan ke susunan bawaan.")
        return redirect("piagam_admin:template", pk=t.pk)
    lebar, tinggi = pdf_mod.ukuran_halaman(t) if t else (297 * 2.8346, 210 * 2.8346)
    return render(request, "piagam/template.html", {
        "menu_aktif": "piagam", "t": t, "form": form, "huruf": [(k, v[0]) for k, v in pdf_mod.HURUF.items()],
        "placeholder": svc.PLACEHOLDER, "lebar_mm": round(lebar / 2.8346, 1), "tinggi_mm": round(tinggi / 2.8346, 1),
        "elemen": t.elemen if t else [],
    })  # fmt: skip


@superadmin_wajib
@require_POST
def template_elemen(request, pk: int):
    t = get_object_or_404(TemplatePiagam, pk=pk)
    try:
        t.elemen = bersihkan_elemen(json.loads(request.body or b"[]"))
    except (ValueError, svc.GagalPiagam) as e:
        return JsonResponse({"ok": False, "pesan": getattr(e, "pesan", "Data tidak valid.")}, status=400)
    t.save(update_fields=["elemen", "diubah_pada"])
    catat(request, "piagam.template_disimpan", t, keterangan=f"{t.nama}: posisi teks ({len(t.elemen)} elemen)")
    return JsonResponse({"ok": True})


@superadmin_wajib
def template_pratinjau(request, pk: int):
    t = get_object_or_404(TemplatePiagam, pk=pk)
    r = HttpResponse(pdf_mod.pratinjau_png(t, svc.data_contoh(t.jenis)), content_type="image/png")
    r["Cache-Control"] = "no-store"
    return r


@superadmin_wajib
def template_pratinjau_pdf(request, pk: int):
    t = get_object_or_404(TemplatePiagam, pk=pk)
    return _pdf(pdf_mod.buat_pdf([(t, svc.data_contoh(t.jenis))]), f"Pratinjau_{_nama_file(t.nama)}.pdf", unduh=False)


@superadmin_wajib
@require_POST
def template_hapus(request, pk: int):
    t = get_object_or_404(TemplatePiagam, pk=pk)
    if t.terbit.exists():
        t.aktif = False
        t.save(update_fields=["aktif", "diubah_pada"])
        messages.warning(request, "Template sudah dipakai piagam terbit, jadi hanya dinonaktifkan.")
    else:
        t.hapus_lunak(oleh=getattr(request, "nama_pelaku", "") or request.user.username)
        messages.success(request, "Template dipindahkan ke tempat sampah.")
    catat(request, "piagam.template_dihapus", t, keterangan=t.nama)
    return redirect("piagam_admin:beranda")
