"""Superadmin: kelola titik absen, kehadiran per titik, pantauan langsung."""

from __future__ import annotations

import contextlib
from datetime import timedelta
from urllib.parse import urlencode

from django import forms
from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.akun.decorators import superadmin_wajib
from apps.biodata.models import Peserta
from apps.inti import pengaturan
from apps.inti.log import catat, selisih

from . import services
from .models import Kegiatan, Kehadiran, PindaianDitolak, StatusTitik, TingkatTitik, TitikAbsen


class FormTitik(forms.ModelForm):
    class Meta:
        model = TitikAbsen
        fields = [
            "kode",
            "nama_tampil",
            "kegiatan",
            "tingkat",
            "tanggal",
            "mulai",
            "selesai",
            "lokasi",
            "status",
            "hitung_poin",
            "catatan",
        ]
        labels = {
            "kode": "Kode",
            "nama_tampil": "Nama di layar pemindai",
            "kegiatan": "Kegiatan (kosongkan untuk titik bebas, misalnya Parade Budaya)",
            "tingkat": "Tingkat",
            "tanggal": "Tanggal",
            "mulai": "Jam mulai",
            "selesai": "Jam selesai (kosongkan bila “selesai”)",
            "lokasi": "Lokasi",
            "status": "Status",
            "hitung_poin": "Dihitung untuk poin kehadiran",
            "catatan": "Catatan",
        }
        widgets = {
            "tanggal": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "mulai": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "selesai": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "catatan": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["kegiatan"].required = False
        self.fields["kegiatan"].empty_label = "(titik bebas)"
        for f in self.fields.values():
            if not isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs.setdefault("class", "input")

    def clean_kode(self) -> str:
        kode = self.cleaned_data["kode"].strip().upper()
        if TitikAbsen.objects.filter(kode=kode).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Kode sudah dipakai titik lain.")
        return kode

    def clean(self):
        data = super().clean()
        if data.get("mulai") and data.get("selesai") and data["selesai"] <= data["mulai"]:
            self.add_error("selesai", "Jam selesai harus setelah jam mulai.")
        return data


def _data(t: TitikAbsen) -> dict:
    return {
        "kode": t.kode, "nama_tampil": t.nama_tampil, "kegiatan": t.kegiatan_id, "tingkat": t.tingkat,
        "tanggal": t.tanggal, "mulai": t.mulai, "selesai": t.selesai, "lokasi": t.lokasi, "status": t.status,
        "hitung_poin": t.hitung_poin,
    }  # fmt: skip


def _kode_berikut() -> str:
    nomor = 0
    for kode in TitikAbsen.objects.filter(kode__startswith="TA-").values_list("kode", flat=True):
        with contextlib.suppress(ValueError):
            nomor = max(nomor, int(kode[3:]))
    return f"TA-{nomor + 1:03d}"


@superadmin_wajib
def titik_daftar(request):
    nilai = pengaturan.semua()
    sekarang = timezone.now()
    qs = TitikAbsen.objects.select_related("kegiatan").annotate(
        hadir=Count("kehadiran", filter=Q(kehadiran__dihapus_pada__isnull=True))
    )
    tanggal = request.GET.get("tanggal", "")
    if tanggal:
        qs = qs.filter(tanggal=tanggal)
    if request.GET.get("tingkat") in TingkatTitik.values:
        qs = qs.filter(tingkat=request.GET["tingkat"])
    if request.GET.get("kegiatan", "").isdigit():
        qs = qs.filter(kegiatan_id=int(request.GET["kegiatan"]))
    baris = list(qs.order_by("tanggal", "mulai", "kode"))
    for t in baris:
        t.kelompok = services.kelompok_titik(t, sekarang, nilai)
    return render(
        request,
        "superadmin/titik_daftar.html",
        {
            "menu_aktif": "titik",
            "baris": baris,
            "daftar_tanggal": TitikAbsen.objects.order_by("tanggal").values_list("tanggal", flat=True).distinct(),
            "daftar_kegiatan": Kegiatan.objects.all(),
            "pilihan_tingkat": TingkatTitik.choices,
            "g": request.GET,
            "menit_sebelum": nilai.get("absensi.menit_sebelum"),
            "menit_sesudah": nilai.get("absensi.menit_sesudah"),
        },
    )


@superadmin_wajib
def titik_form(request, pk: int | None = None):
    t = get_object_or_404(TitikAbsen, pk=pk) if pk else None
    lama = _data(t) if t else None
    awal = {} if t else {"kode": _kode_berikut(), "tanggal": timezone.localdate()}
    form = FormTitik(request.POST or None, instance=t, initial=awal)
    if request.method == "POST" and form.is_valid():
        t = form.save()
        if lama is None:
            catat(request, "titik_absen.dibuat", t, keterangan=f"{t.kode} {t.nama_tampil}", baru=_data(t))
        else:
            d_lama, d_baru = selisih(lama, _data(t))
            if d_baru:
                catat(request, "titik_absen.diubah", t, keterangan=t.kode, lama=d_lama, baru=d_baru)
        messages.success(request, f"Titik absen {t.kode} disimpan.")
        return redirect("absensi_admin:titik_detail", pk=t.pk)
    return render(request, "superadmin/titik_form.html", {"menu_aktif": "titik", "form": form, "t": t})


@superadmin_wajib
@require_POST
def titik_status(request, pk: int):
    t = get_object_or_404(TitikAbsen, pk=pk)
    status = request.POST.get("status")
    if status in StatusTitik.values and status != t.status:
        lama = t.status
        t.status = status
        t.save(update_fields=["status", "diubah_pada"])
        catat(request, "titik_absen.status", t, keterangan=f"{t.kode}: {lama} -> {status}")
        messages.success(request, f"Status {t.kode}: {t.get_status_display()}.")
    kembali = request.POST.get("kembali", "")
    return redirect(kembali if kembali.startswith("/superadmin/") else "absensi_admin:titik_daftar")


@superadmin_wajib
@require_POST
def titik_salin(request, pk: int):
    """Salin titik untuk hari lain (kode baru, jam dan lokasi sama)."""
    t = get_object_or_404(TitikAbsen, pk=pk)
    try:
        tanggal = timezone.datetime.fromisoformat(request.POST.get("tanggal", "")).date()
    except ValueError:
        messages.error(request, "Pilih tanggal tujuan.")
        return redirect("absensi_admin:titik_detail", pk=t.pk)
    baru = TitikAbsen.objects.create(
        kode=_kode_berikut(), kegiatan=t.kegiatan, tingkat=t.tingkat, nama_tampil=t.nama_tampil, tanggal=tanggal,
        mulai=t.mulai, selesai=t.selesai, lokasi=t.lokasi, status=StatusTitik.OTOMATIS, hitung_poin=t.hitung_poin,
        catatan=f"Salinan dari {t.kode}",
    )  # fmt: skip
    catat(request, "titik_absen.disalin", baru, keterangan=f"{t.kode} -> {baru.kode} ({tanggal:%d/%m/%Y})")
    messages.success(request, f"Titik {baru.kode} dibuat dari {t.kode}. Periksa nama tampilnya.")
    return redirect("absensi_admin:titik_ubah", pk=baru.pk)


@superadmin_wajib
@require_POST
def titik_hapus(request, pk: int):
    t = get_object_or_404(TitikAbsen, pk=pk)
    if Kehadiran.semua.filter(titik_absen=t).exists():
        messages.error(
            request,
            "Titik ini sudah punya catatan kehadiran, jadi tidak bisa dihapus. Ubah status menjadi Tutup paksa.",
        )
        return redirect("absensi_admin:titik_detail", pk=t.pk)
    catat(request, "titik_absen.dihapus", t, keterangan=f"{t.kode} {t.nama_tampil}", lama=_data(t))
    PindaianDitolak.objects.filter(titik_absen=t).update(titik_absen=None)
    t.delete()
    messages.success(request, "Titik absen dihapus.")
    return redirect("absensi_admin:titik_daftar")


@superadmin_wajib
def titik_detail(request, pk: int):
    t = get_object_or_404(TitikAbsen.objects.select_related("kegiatan"), pk=pk)
    hadir = list(
        Kehadiran.objects.filter(titik_absen=t).select_related("peserta__kontingen").order_by("-diterima_pada")
    )
    q = " ".join(request.GET.get("q", "").split())[:60]
    kandidat = []
    if len(q) >= 2:
        sudah = {k.peserta_id for k in hadir}
        kode = q.upper().replace(" ", "").replace("-", "")
        filter_kode = Q(kode_kartu=f"{kode[:4]}-{kode[4:8]}") if len(kode) == 8 else Q()
        kandidat = list(
            Peserta.objects.filter(Q(nama_lengkap__icontains=q) | filter_kode).select_related("kontingen")[:20]
        )
        for p in kandidat:
            p.sudah_hadir = p.pk in sudah
            p.tingkat_beda = t.tingkat != TingkatTitik.SEMUA and p.tingkat != t.tingkat
    ditolak = PindaianDitolak.objects.filter(titik_absen=t).select_related("peserta").order_by("-dibuat_pada")[:20]
    mulai, akhir = services.jendela_titik(t)
    return render(
        request,
        "superadmin/titik_detail.html",
        {
            "menu_aktif": "titik",
            "t": t,
            "hadir": hadir,
            "terbuka": services.titik_terbuka(t),
            "jendela_mulai": mulai,
            "jendela_akhir": akhir,
            "q": q,
            "kandidat": kandidat,
            "ditolak": ditolak,
            "pilihan_status": StatusTitik.choices,
        },
    )


@superadmin_wajib
@require_POST
def kehadiran_batal(request, pk: int):
    k = get_object_or_404(Kehadiran.objects.select_related("peserta", "titik_absen"), pk=pk)
    services.batalkan_kehadiran(request, k)
    messages.success(request, f"Kehadiran {k.peserta.nama_lengkap} di {k.titik_absen.kode} dibatalkan.")
    return redirect("absensi_admin:titik_detail", pk=k.titik_absen_id)


@superadmin_wajib
@require_POST
def kehadiran_tambah(request, pk: int):
    t = get_object_or_404(TitikAbsen, pk=pk)
    p = get_object_or_404(Peserta, pk=request.POST.get("peserta") or 0)
    alasan = " ".join(request.POST.get("alasan", "").split())[:200]
    if len(alasan) < 3:
        messages.error(request, "Tulis alasan absen manual (misalnya: kartu tertinggal).")
        return redirect(f"{reverse('absensi_admin:titik_detail', args=[t.pk])}?{urlencode({'q': p.nama_lengkap})}")
    hasil = services.tambah_manual(request, t, p, alasan, izinkan_tingkat_beda=request.POST.get("izinkan") == "1")
    tingkat = messages.success if hasil.status == "HIJAU" else messages.warning
    tingkat(request, f"{p.nama_lengkap}: {hasil.pesan}")
    return redirect("absensi_admin:titik_detail", pk=t.pk)


@superadmin_wajib
def pantauan(request):
    return render(request, "superadmin/pantauan.html", {"menu_aktif": "pantauan"})


@superadmin_wajib
def pantauan_json(request):
    """Data pantauan langsung (polling): titik yang sedang berlangsung, HP aktif, pindaian merah terbaru."""
    nilai = pengaturan.semua()
    sekarang = timezone.now()
    lima_menit = sekarang - timedelta(minutes=5)
    hari_ini = timezone.localdate()
    titik = [
        t
        for t in TitikAbsen.objects.filter(
            tanggal__gte=hari_ini - timedelta(days=1), tanggal__lte=hari_ini + timedelta(days=1)
        )
        if services.titik_terbuka(t, sekarang, nilai)
    ] + list(
        TitikAbsen.objects.filter(status=StatusTitik.BUKA).exclude(
            tanggal__range=(hari_ini - timedelta(days=1), hari_ini + timedelta(days=1))
        )
    )
    hasil = []
    for t in titik:
        qs = Kehadiran.objects.filter(titik_absen=t)
        agregat = qs.aggregate(hadir=Count("id"), kontingen=Count("peserta__kontingen", distinct=True))
        hp = set(qs.filter(diterima_pada__gte=lima_menit).values_list("perangkat_id", flat=True))
        hp |= set(
            PindaianDitolak.objects.filter(titik_absen=t, dibuat_pada__gte=lima_menit).values_list(
                "perangkat_id", flat=True
            )
        )
        terakhir = qs.order_by("-diterima_pada").values_list("diterima_pada", flat=True).first()
        hasil.append({
            "id": t.pk, "kode": t.kode, "nama": t.nama_tampil, "tingkat": t.tingkat,
            "jam": f"{t.mulai:%H.%M}-{t.selesai:%H.%M}" if t.selesai else f"{t.mulai:%H.%M}-selesai",
            "hadir": agregat["hadir"], "kontingen": agregat["kontingen"], "hp_aktif": len(hp - {""}),
            "terakhir": f"{timezone.localtime(terakhir):%H.%M}" if terakhir else "-",
        })  # fmt: skip
    merah = [
        {
            "jam": f"{timezone.localtime(d.dibuat_pada):%H.%M.%S}",
            "titik": d.titik_absen.kode if d.titik_absen else "-",
            "kode": d.kode,
            "nama": d.peserta.nama_lengkap if d.peserta else "",
            "oleh": d.nama_pemindai,
        }
        for d in PindaianDitolak.objects.select_related("titik_absen", "peserta").order_by("-dibuat_pada")[:15]
    ]
    total_hp = set(Kehadiran.objects.filter(diterima_pada__gte=lima_menit).values_list("perangkat_id", flat=True))
    return JsonResponse(
        {
            "jam": f"{timezone.localtime(sekarang):%H.%M.%S}",
            "titik": sorted(hasil, key=lambda x: x["kode"]),
            "merah": merah,
            "hp_aktif": len(total_hp - {""}),
            "pindaian_5_menit": Kehadiran.objects.filter(diterima_pada__gte=lima_menit).count(),
        }
    )


# --- Kegiatan dan kuota -----------------------------------------------------------------


def _angka_kuota(teks: str) -> int | None | str:
    """'' -> None (kosong), angka 0-500 -> int, selain itu 'salah'."""
    teks = (teks or "").strip()
    if teks == "":
        return None
    if not teks.isdigit() or int(teks) > 500:
        return "salah"
    return int(teks)


@superadmin_wajib
def kegiatan_daftar(request):
    daftar = list(Kegiatan.objects.annotate(n_khusus=Count("kuota", filter=Q(kuota__kontingen__isnull=False))))
    if request.method == "POST":
        berubah = []
        for kg in daftar:
            nilai = _angka_kuota(request.POST.get(f"kuota_{kg.pk}", ""))
            if nilai == "salah":
                messages.error(request, f"Kuota {kg.nama} harus angka 0-500 atau kosong.")
                return redirect("absensi_admin:kegiatan_daftar")
            if nilai != kg.kuota_default:
                berubah.append((kg, kg.kuota_default, nilai))
        batasi = request.POST.get("batasi") == "1"
        for kg, lama, baru in berubah:
            kg.kuota_default = baru
            kg.save(update_fields=["kuota_default", "diubah_pada"])
            catat(
                request,
                "kegiatan.kuota_diubah",
                kg,
                keterangan=kg.nama,
                lama={"kuota_default": lama},
                baru={"kuota_default": baru},
            )
        if batasi != bool(pengaturan.ambil("poin.batasi_ke_kuota", True)):
            pengaturan.simpan("poin.batasi_ke_kuota", batasi, request.nama_pelaku or request.user.username)
            catat(
                request, "pengaturan.diubah", keterangan="poin.batasi_ke_kuota", baru={"poin.batasi_ke_kuota": batasi}
            )
        messages.success(request, f"Kuota disimpan ({len(berubah)} kegiatan berubah).")
        return redirect("absensi_admin:kegiatan_daftar")
    return render(
        request,
        "superadmin/kegiatan_daftar.html",
        {"menu_aktif": "kegiatan_kuota", "daftar": daftar, "batasi": pengaturan.ambil("poin.batasi_ke_kuota", True)},
    )


@superadmin_wajib
def kegiatan_kuota(request, pk: int):
    """Kuota khusus per kontingen untuk satu kegiatan (kosong = ikut kuota bawaan)."""
    from apps.kontingen.models import URUTAN_TINGKAT, Kontingen

    from .models import KuotaKegiatan

    kg = get_object_or_404(Kegiatan, pk=pk)
    kontingen = list(Kontingen.objects.order_by(URUTAN_TINGKAT, "kode"))
    khusus = {k.kontingen_id: k for k in KuotaKegiatan.objects.filter(kegiatan=kg).exclude(kontingen=None)}
    if request.method == "POST":
        jumlah = 0
        for k in kontingen:
            nilai = _angka_kuota(request.POST.get(f"k_{k.pk}", ""))
            if nilai == "salah":
                messages.error(request, f"Kuota {k.nama} harus angka 0-500 atau kosong.")
                return redirect("absensi_admin:kegiatan_kuota", pk=kg.pk)
            ada = khusus.get(k.pk)
            lama = ada.kuota if ada else None
            if nilai == lama:
                continue
            if nilai is None:
                ada.delete()
            elif ada:
                ada.kuota = nilai
                ada.save(update_fields=["kuota", "diubah_pada"])
            else:
                KuotaKegiatan.objects.create(kegiatan=kg, kontingen=k, kuota=nilai)
            catat(
                request,
                "kegiatan.kuota_kontingen",
                kg,
                keterangan=f"{kg.nama} {k.kode}",
                lama={"kuota": lama},
                baru={"kuota": nilai},
            )
            jumlah += 1
        messages.success(request, f"Kuota khusus {kg.nama} disimpan ({jumlah} kontingen berubah).")
        return redirect("absensi_admin:kegiatan_kuota", pk=kg.pk)
    baris = [{"k": k, "nilai": khusus[k.pk].kuota if k.pk in khusus else ""} for k in kontingen]
    return render(request, "superadmin/kegiatan_kuota.html", {"menu_aktif": "kegiatan_kuota", "kg": kg, "baris": baris})
