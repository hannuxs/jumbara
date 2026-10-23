"""Form builder untuk superadmin: kelola form, kolom, rumus, hasil, kiriman."""

from __future__ import annotations

import json
from collections import Counter

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.absensi.views_rekap import excel
from apps.akun.decorators import superadmin_wajib
from apps.inti.log import catat
from apps.inti.models import Tingkat

from . import hasil as hs
from . import rumus as r
from . import services as svc
from .forms import FormIsian
from .forms_admin import FormPengaturan
from .models import (
    JENIS_INPUT,
    AksesForm,
    Formulir,
    JenisKolom,
    Kiriman,
    Kolom,
    ModeForm,
    StatusForm,
    SumberOtomatis,
)

FUNGSI_BANTUAN = [
    ("SUM(a, b, ...)", "Jumlah"),
    ("AVG(a, b, ...)", "Rata-rata (yang kosong diabaikan)"),
    ("MIN(...) / MAX(...)", "Terkecil / terbesar"),
    ("ROUND(x, 2)", "Bulatkan ke 2 desimal"),
    ("ABS(x)", "Nilai mutlak"),
    ("IF(syarat, jika_ya, jika_tidak)", "Contoh IF([a] >= 75, 10, 0)"),
    ("COALESCE(x, cadangan)", "Pakai cadangan bila x kosong"),
    ("ISBLANK(x)", "1 bila kosong, 0 bila terisi"),
    ('REF("slug-form", "kode")', "Ambil nilai kolom dari form lain untuk subjek yang sama"),
    ('REF("anjangsana", "rata_rata")', "Hasil Anjangsana: rata_rata, jumlah_kunjungan, peringkat, ..."),
    ("PERINGKAT([kolom])", 'Peringkat di form ini (tambah "NAIK" bila terkecil juara)'),
    ("POIN_PERINGKAT(p, 10, 8, 6)", "Juara 1 = 10, juara 2 = 8, juara 3 = 6, lainnya 0"),
]


def tampil(nilai, desimal: int = 2) -> str:
    if nilai is None:
        return ""
    if float(nilai) == int(nilai):
        return f"{int(nilai)}"
    return f"{nilai:.{desimal}f}".replace(".", ",")


def _form(pk: int) -> Formulir:
    return get_object_or_404(Formulir, pk=pk)


# --- Daftar dan pengaturan ------------------------------------------------------------------------------


@superadmin_wajib
def daftar(request):
    qs = Formulir.objects.select_related("kegiatan").annotate(
        n_kiriman=Count("kiriman", filter=Q(kiriman__dihapus_pada__isnull=True))
    )
    g = {k: request.GET.get(k, "") for k in ("mode", "status", "tingkat", "q")}
    if g["mode"] in ModeForm.values:
        qs = qs.filter(mode=g["mode"])
    if g["status"] in StatusForm.values:
        qs = qs.filter(status=g["status"])
    else:
        qs = qs.exclude(status=StatusForm.ARSIP)
    if g["tingkat"]:
        qs = qs.filter(tingkat=g["tingkat"])
    if g["q"]:
        qs = qs.filter(Q(judul__icontains=g["q"]) | Q(slug__icontains=g["q"]))
    qs = qs.order_by("kegiatan__urutan", "judul")
    return render(request, "penilaian/admin_daftar.html", {
        "menu_aktif": "form", "daftar": qs, "g": g, "mode": ModeForm.choices, "status": StatusForm.choices,
        "tingkat": [*Tingkat.choices, ("SEMUA", "Semua tingkat")],
    })  # fmt: skip


@superadmin_wajib
def pengaturan(request, pk: int | None = None):
    f = _form(pk) if pk else None
    awal = {} if f else {"mode": request.GET.get("mode") or ModeForm.INPUT}
    form = FormPengaturan(request.POST or None, instance=f, initial=awal)
    if request.method == "POST" and form.is_valid():
        baru = f is None
        f = form.save()
        catat(request, "form.dibuat" if baru else "form.pengaturan_diubah", f, keterangan=f"{f.slug}")
        messages.success(request, f'Form "{f.judul}" disimpan.')
        return redirect("penilaian_admin:detail", pk=f.pk)
    return render(request, "penilaian/admin_pengaturan.html", {"menu_aktif": "form", "form": form, "f": f})


@superadmin_wajib
def detail(request, pk: int):
    f = _form(pk)
    kolom = list(f.kolom.all())
    return render(request, "penilaian/admin_detail.html", {
        "menu_aktif": "form", "f": f, "kolom": kolom, "jenis": JenisKolom.choices, "n_kiriman": f.kiriman.count(),
        "url_publik": request.build_absolute_uri(f"/f/{f.slug}/") if f.akses == AksesForm.PUBLIK else "",
    })  # fmt: skip


@superadmin_wajib
@require_POST
def status(request, pk: int):
    f = _form(pk)
    nilai = request.POST.get("status")
    if nilai in StatusForm.values and nilai != f.status:
        if (
            nilai == StatusForm.AKTIF
            and not f.kolom.filter(jenis__in=list(JENIS_INPUT)).exists()
            and f.mode == ModeForm.INPUT
        ):
            messages.error(request, "Tambahkan minimal satu isian sebelum mengaktifkan form.")
            return redirect("penilaian_admin:detail", pk=f.pk)
        lama = f.status
        f.status = nilai
        f.save(update_fields=["status", "diubah_pada"])
        catat(request, "form.status", f, keterangan=f"{f.slug}: {lama} -> {nilai}")
        messages.success(request, f"Status form: {f.get_status_display()}.")
    return redirect("penilaian_admin:detail", pk=f.pk)


@superadmin_wajib
@require_POST
def salin(request, pk: int):
    f = _form(pk)
    tingkat = request.POST.get("tingkat") or None
    if tingkat and tingkat not in ("MULA", "MADYA", "WIRA", "SEMUA"):
        tingkat = None
    baru = svc.salin_form(request, f, tingkat=tingkat, judul=(request.POST.get("judul") or "").strip() or None)
    messages.success(request, f'Form disalin menjadi "{baru.judul}" (draf).')
    return redirect("penilaian_admin:detail", pk=baru.pk)


@superadmin_wajib
@require_POST
def hapus(request, pk: int):
    f = _form(pk)
    f.hapus_lunak(oleh=svc.nama_pelaku(request))
    catat(request, "form.dihapus", f, keterangan=f.slug)
    messages.success(request, f'Form "{f.judul}" dipindahkan ke tempat sampah.')
    return redirect("penilaian_admin:daftar")


@superadmin_wajib
@require_POST
def kunci(request, pk: int):
    f = _form(pk)
    svc.atur_kunci_form(request, f, request.POST.get("kunci") == "1")
    messages.success(
        request, "Form dikunci: juri tidak bisa mengirim/mengubah nilai." if f.terkunci else "Kunci form dibuka."
    )
    kembali = request.POST.get("kembali", "")
    return redirect(kembali if kembali.startswith("/superadmin/form/") else f"/superadmin/form/{f.pk}/hasil/")


# --- Kolom -----------------------------------------------------------------------------------------------------


@superadmin_wajib
def kolom_form(request, pk: int, kid: int | None = None):
    f = _form(pk)
    k = get_object_or_404(Kolom, pk=kid, formulir=f) if kid else None
    galat = ""
    if request.method == "POST":
        data = request.POST.dict()
        data["pilihan"] = request.POST.get("pilihan", "")
        try:
            k = svc.simpan_kolom(request, f, data, kolom=k)
        except svc.GagalForm as e:
            galat = e.pesan
        else:
            messages.success(request, f"Kolom [{k.kode}] disimpan.")
            if request.POST.get("lanjut"):
                return redirect("penilaian_admin:kolom_tambah", pk=f.pk)
            return redirect("penilaian_admin:detail", pk=f.pk)
    awal = request.POST.dict() if request.method == "POST" else _awal_kolom(k, request.GET.get("jenis"))
    jenis = [
        (v, label) for v, label in JenisKolom.choices if f.penilaian or v not in ("OTOMATIS", "RUMUS", "PERINGKAT")
    ]
    return render(request, "penilaian/admin_kolom.html", {
        "menu_aktif": "form", "f": f, "k": k, "awal": awal, "galat": galat, "jenis": jenis,
        "tersedia": hs.nama_tersedia(f, kecuali=getattr(k, "kode", None)), "fungsi": FUNGSI_BANTUAN,
        "sumber": SumberOtomatis.choices, "form_lain": _form_ref(f),
    })  # fmt: skip


def _awal_kolom(k: Kolom | None, jenis: str | None) -> dict:
    if k is None:
        return {"jenis": jenis if jenis in JenisKolom.values else JenisKolom.ANGKA, "tampil_desimal": "2", "wajib": "1"}
    p = k.pengaturan or {}
    awal = {"jenis": k.jenis, "label": k.label, "kode": k.kode, "bantuan": k.bantuan, "wajib": "1" if k.wajib else ""}
    for kunci in ("min", "max", "desimal", "sumber", "rumus", "dasar", "arah", "ukuran_mb", "tampil_desimal", "maks"):
        if p.get(kunci) is not None:
            v = p[kunci]
            awal[kunci] = f"{v:g}" if isinstance(v, float) else str(v)
    awal["pilihan"] = "\n".join(p.get("pilihan", []))
    awal["tipe_berkas"] = ", ".join(p.get("tipe_berkas", []))
    return awal


def _form_ref(f: Formulir) -> list[dict]:
    hasil = [{"slug": "anjangsana", "judul": "Hasil Anjangsana", "kolom": list(hs.KOLOM_ANJANGSANA)}]
    for x in (
        Formulir.objects.filter(mode=ModeForm.PENILAIAN)
        .exclude(pk=f.pk)
        .exclude(status=StatusForm.ARSIP)
        .order_by("judul")
    ):
        hasil.append({"slug": x.kunci_ref or x.slug, "judul": f"{x.judul} ({x.get_tingkat_display()})",
                      "kolom": sorted(hs.kolom_sumber(x))})  # fmt: skip
    return hasil


@superadmin_wajib
@require_POST
def kolom_hapus(request, pk: int, kid: int):
    f = _form(pk)
    k = get_object_or_404(Kolom, pk=kid, formulir=f)
    try:
        svc.hapus_kolom(request, k)
    except svc.GagalForm as e:
        messages.error(request, e.pesan)
    else:
        messages.success(request, f"Kolom [{k.kode}] dihapus.")
    return redirect("penilaian_admin:detail", pk=f.pk)


@superadmin_wajib
@require_POST
def kolom_urutan(request, pk: int):
    f = _form(pk)
    try:
        daftar_id = [int(x) for x in json.loads(request.body or b"[]")]
        svc.urutkan_kolom(request, f, daftar_id)
    except (ValueError, TypeError):
        return JsonResponse({"ok": False, "pesan": "Data urutan tidak valid."}, status=400)
    except svc.GagalForm as e:
        return JsonResponse({"ok": False, "pesan": e.pesan}, status=400)
    return JsonResponse({"ok": True})


@superadmin_wajib
@require_POST
def rumus_cek(request, pk: int):
    """Validasi langsung + pratinjau hasil untuk beberapa subjek contoh (tanpa menyimpan)."""
    f = _form(pk)
    try:
        data = json.loads(request.body or b"{}")
    except ValueError:
        return JsonResponse({"ok": False, "pesan": "Data tidak valid."}, status=400)
    kode = str(data.get("kode") or "_pratinjau")[:40].lower()
    teks = str(data.get("rumus") or "")[: r.BATAS_PANJANG + 1]
    try:
        pohon = hs.validasi_rumus(f, kode, teks)
    except r.GalatRumus as e:
        return JsonResponse({"ok": False, "pesan": str(e), "posisi": e.posisi})
    tabel = hs.tabel_hasil(f)
    penghitung = hs.Penghitung()
    contoh = []
    for b in tabel.baris[:5]:
        k = r.Konteks(nilai=lambda x, b=b: b.nilai.get(x),
                      ref=lambda slug, kk, ti, b=b: penghitung.nilai_ref(slug, kk, ti, b.subjek, b.peringatan))  # fmt: skip
        v = r.hitung_aman(pohon, k, kode)
        contoh.append({"subjek": b.subjek.label, "nilai": tampil(v, 4) if v is not None else "(kosong)",
                       "peringatan": k.peringatan[:2]})  # fmt: skip
    return JsonResponse({"ok": True, "pesan": "Rumus benar.", "contoh": contoh})


# --- Isi dan pratinjau -------------------------------------------------------------------------------------------


@superadmin_wajib
def pratinjau(request, pk: int):
    f = _form(pk)
    form = FormIsian(list(f.kolom.all()), label_nama="Nama Juri" if f.penilaian else "Nama pengisi")
    return render(request, "penilaian/isi.html", {
        "f": f, "form": form, "pratinjau": True, "subjek": hs.daftar_subjek(f)[:1], "kembali": f"/superadmin/form/{f.pk}/",
    })  # fmt: skip


# --- Hasil ---------------------------------------------------------------------------------------------------------


@superadmin_wajib
def hasil(request, pk: int):
    f = _form(pk)
    if not f.penilaian:
        return _hasil_input(request, f)
    tabel = hs.tabel_hasil(f)
    kolom_tampil = [k for k in tabel.kolom if k.jenis != JenisKolom.JUDUL and (k.dihitung or hs.kolom_angka(k))]
    if request.GET.get("unduh") == "xlsx":
        kepala = ["Peringkat", "Seri", "Subjek", "Tingkat"] + [f"{k.label} [{k.kode}]" for k in kolom_tampil]
        kepala += tabel.bawaan_tampil + ["Jumlah juri", "Juri"]
        baris = []
        for b in sorted(tabel.baris, key=lambda x: (x.peringkat is None, x.peringkat or 0, x.subjek.label)):
            baris.append([b.peringkat, "seri" if b.seri else "", b.subjek.label, b.subjek.tingkat.title()]
                         + [b.nilai.get(k.kode) for k in kolom_tampil] + [b.nilai.get(x) for x in tabel.bawaan_tampil]
                         + [b.jumlah_juri, ", ".join(x.nama_pengisi for x in b.kiriman)])  # fmt: skip
        return excel(request, f"Hasil {f.judul}", kepala, baris, f"hasil-{f.slug}")
    if request.method == "POST" and request.POST.get("aksi") == "pemecah":
        nilai = {}
        for b in tabel.baris:
            v = request.POST.get(f"ps_{b.subjek.kunci}", "").strip()
            nilai[b.subjek.kunci] = int(v) if v.isdigit() and 0 < int(v) < 1000 else None
        svc.simpan_pemecah_seri(request, f, nilai)
        messages.success(request, "Pemecah seri disimpan.")
        return redirect("penilaian_admin:hasil", pk=f.pk)
    urut = request.GET.get("urut", "")
    baris = list(tabel.baris)
    if urut.lstrip("-") in {k.kode for k in kolom_tampil} | set(tabel.bawaan_tampil):
        kode = urut.lstrip("-")
        baris.sort(
            key=lambda b: (
                b.nilai.get(kode) is None,
                -(b.nilai.get(kode) or 0) if urut.startswith("-") else (b.nilai.get(kode) or 0),
            )
        )
    else:
        baris.sort(key=lambda b: (b.peringkat is None, b.peringkat or 0, b.subjek.label))
    ada_seri = any(b.seri for b in baris)
    return render(request, "penilaian/admin_hasil.html", {
        "menu_aktif": "form", "f": f, "tabel": tabel, "baris": baris, "kolom_tampil": kolom_tampil, "urut": urut,
        "ada_seri": ada_seri, "dinilai": sum(1 for b in baris if not b.belum_dinilai),
        **_konteks_piagam(f),
    })  # fmt: skip


def _konteks_piagam(f: Formulir) -> dict:
    from apps.piagam.models import JenisPiagam, PiagamTerbit, TemplatePiagam
    from apps.piagam.services import pastikan_template_bawaan
    from apps.piagam.views_admin import kegiatan_dari_form

    pastikan_template_bawaan()
    return {
        "template_juara": TemplatePiagam.objects.filter(jenis=JenisPiagam.JUARA, aktif=True),
        "kegiatan_piagam": kegiatan_dari_form(f),
        "n_piagam": PiagamTerbit.objects.filter(sumber=f"form:{f.pk}").count(),
    }


def _hasil_input(request, f: Formulir):
    kolom = [k for k in f.kolom.all() if k.diisi]
    qs = Kiriman.objects.filter(formulir=f).select_related("kontingen", "peserta")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(nama_pengisi__icontains=q) | Q(kontingen__nama__icontains=q) | Q(peserta__nama_lengkap__icontains=q)
        )
    urut = request.GET.get("urut", "-dikirim_pada")
    qs = qs.order_by(
        urut if urut in ("dikirim_pada", "-dikirim_pada", "nama_pengisi", "-nama_pengisi") else "-dikirim_pada"
    )
    if request.GET.get("unduh") == "xlsx":
        kepala = ["Waktu", "Pengisi", "Subjek"] + [f"{k.label} [{k.kode}]" for k in kolom]
        baris = [[x.dikirim_pada.strftime("%d/%m/%Y %H:%M"), x.nama_pengisi, _label_subjek(x)]
                 + [_isi_teks(k, x.data.get(k.kode)) for k in kolom] for x in qs]  # fmt: skip
        return excel(request, f"Kiriman {f.judul}", kepala, baris, f"kiriman-{f.slug}")
    rekap = _rekap(kolom, list(qs))
    halaman = Paginator(qs, 50).get_page(request.GET.get("hal"))
    return render(request, "penilaian/admin_kiriman.html", {
        "menu_aktif": "form", "f": f, "kolom": kolom[:6], "halaman": halaman, "q": q, "rekap": rekap, "total": qs.count(),
    })  # fmt: skip


def _label_subjek(x: Kiriman) -> str:
    if x.kontingen_id:
        return x.kontingen.nama
    if x.peserta_id:
        return x.peserta.nama_lengkap
    return x.data.get("_subjek", "")


def _isi_teks(k: Kolom, v) -> str | float | int:
    if v is None:
        return ""
    if isinstance(v, list):
        return ", ".join(map(str, v))
    if isinstance(v, dict) and "file" in v:
        return v.get("nama", "file")
    return v


def _rekap(kolom: list[Kolom], kiriman: list[Kiriman]) -> list[dict]:
    hasil = []
    for k in kolom:
        isi = [x.data.get(k.kode) for x in kiriman if x.data.get(k.kode) not in (None, "", [])]
        item = {"k": k, "terisi": len(isi)}
        angka = [hs.nilai_angka(k, v) for v in isi]
        angka = [a for a in angka if a is not None]
        if k.jenis in (JenisKolom.ANGKA, JenisKolom.SKALA) and angka:
            item["rata"] = tampil(sum(angka) / len(angka))
            item["min"], item["max"] = tampil(min(angka)), tampil(max(angka))
        if k.jenis in (
            JenisKolom.PILIHAN,
            JenisKolom.DROPDOWN,
            JenisKolom.CENTANG,
            JenisKolom.YA_TIDAK,
            JenisKolom.SKALA,
        ):
            hitung = Counter()
            for v in isi:
                for x in v if isinstance(v, list) else [v]:
                    hitung[str(x)] += 1
            urutan = k.atur("pilihan") or (["ya", "tidak"] if k.jenis == JenisKolom.YA_TIDAK else sorted(hitung))
            maks = max(hitung.values(), default=1)
            item["batang"] = [
                {"label": p, "n": hitung.get(str(p), 0), "persen": round(100 * hitung.get(str(p), 0) / maks)}
                for p in urutan
            ]
        hasil.append(item)
    return hasil


# --- Kiriman ---------------------------------------------------------------------------------------------------------


@superadmin_wajib
def kiriman_detail(request, pk: int, xid: int):
    f = _form(pk)
    x = get_object_or_404(Kiriman, pk=xid, formulir=f)
    kolom = list(f.kolom.all())
    form = None
    if request.method == "POST" and request.POST.get("aksi") == "ubah":
        form = FormIsian(kolom, request.POST, request.FILES, label_nama="Nama Juri" if f.penilaian else "Nama pengisi")
        for k in kolom:
            if k.jenis == JenisKolom.BERKAS and f"k_{k.kode}" in form.fields:
                form.fields[f"k_{k.kode}"].required = False  # file lama dipertahankan
        if form.is_valid():
            data, berkas = form.data_bersih()
            svc.ubah_kiriman(request, x, data, berkas, form.cleaned_data["nama_pengisi"])
            messages.success(request, "Kiriman diubah (isi lama tersimpan di riwayat).")
            return redirect("penilaian_admin:kiriman", pk=f.pk, xid=x.pk)
    elif request.method == "POST" and request.POST.get("aksi") in ("buka", "kunci"):
        svc.atur_kunci_kiriman(request, x, request.POST["aksi"] == "kunci")
        messages.success(
            request,
            "Kiriman dibuka: juri bisa mengirim ulang nilai untuk subjek ini."
            if not x.terkunci
            else "Kiriman dikunci.",
        )
        return redirect("penilaian_admin:kiriman", pk=f.pk, xid=x.pk)
    elif request.method == "POST" and request.POST.get("aksi") == "hapus":
        svc.hapus_kiriman(request, x)
        messages.success(request, "Kiriman dipindahkan ke tempat sampah.")
        return redirect("penilaian_admin:hasil", pk=f.pk)
    if form is None and request.GET.get("ubah"):
        form = FormIsian(kolom, initial={"nama_pengisi": x.nama_pengisi}, awal_data=x.data,
                         label_nama="Nama Juri" if f.penilaian else "Nama pengisi")  # fmt: skip
        for k in kolom:
            if k.jenis == JenisKolom.BERKAS and f"k_{k.kode}" in form.fields:
                form.fields[f"k_{k.kode}"].required = False
    isian = [(k, x.data.get(k.kode)) for k in kolom if k.diisi or k.jenis == JenisKolom.JUDUL]
    return render(request, "penilaian/admin_kiriman_detail.html", {
        "menu_aktif": "form", "f": f, "x": x, "isian": isian, "form": form, "subjek": _label_subjek(x),
    })  # fmt: skip


@superadmin_wajib
def berkas(request, pk: int, xid: int, kode: str):
    f = _form(pk)
    x = get_object_or_404(Kiriman, pk=xid, formulir=f)
    info = x.data.get(kode)
    if not isinstance(info, dict) or "file" not in info:
        raise Http404
    p = svc.path_berkas(f, info["file"])
    if p is None:
        raise Http404
    catat(request, "form.berkas_dibuka", f, keterangan=f"Kiriman #{x.pk} [{kode}] {info.get('nama', '')}"[:255])
    return FileResponse(open(p, "rb"), as_attachment=True, filename=info.get("nama") or p.name)
