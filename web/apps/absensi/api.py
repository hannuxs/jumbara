"""API JSON untuk HP pemindai (akun panitia dan superadmin).

Semua permintaan POST membawa token CSRF Django di header `X-CSRFToken`. Data yang dikirim ke
panitia hanya nama, kontingen, tingkat, peran (tanpa data pribadi lain).
"""

from __future__ import annotations

import hashlib
import json
from functools import wraps

from django.db.models import Count, Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.biodata.models import Peserta
from apps.inti import pengaturan
from apps.kontingen.models import Kontingen

from . import services
from .models import Kehadiran, TingkatTitik, TitikAbsen

BATAS_BATCH = 50


def api_peran(*peran: str):
    """Seperti peran_wajib, tetapi selalu menjawab JSON (HP pemindai tidak boleh dialihkan ke HTML)."""

    def pembungkus(view):
        @wraps(view)
        def _view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({"galat": "BELUM_MASUK", "pesan": "Silakan masuk lagi."}, status=401)
            if request.user.peran not in peran:
                return JsonResponse({"galat": "DILARANG", "pesan": "Akun ini tidak boleh memindai."}, status=403)
            return view(request, *args, **kwargs)

        return _view

    return pembungkus


def _json_body(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return None


def hash_token(token: str) -> str:
    """Sidik token untuk cache nama di HP (token asli tidak dikirim ke daftar)."""
    return hashlib.sha256(token.encode()).hexdigest()[:16]


def _jumlah_kontingen(tingkat: set[str]) -> int:
    qs = Kontingen.objects.all()
    if TingkatTitik.SEMUA not in tingkat:
        qs = qs.filter(tingkat__in=tingkat)
    return qs.count()


def _saring_tingkat(qs, tingkat: set[str]):
    return qs if TingkatTitik.SEMUA in tingkat else qs.filter(tingkat__in=tingkat)


URUT_KELOMPOK = ["BERLANGSUNG", "NANTI_HARI_INI", "SUDAH_LEWAT", "HARI_LAIN", "TUTUP"]


def _sesi_dari_titik(daftar: list[dict]) -> list[dict]:
    """Gabungkan titik kegiatan yang sama pada hari yang sama menjadi satu pilihan di pemindai (R15).

    `id` = titik wakil (pk terkecil); server memilih titik yang sesuai tingkat orang saat memindai.
    """
    sesi: dict[str, dict] = {}
    for t in daftar:
        s = sesi.get(t["sesi"])
        if s is None:
            sesi[t["sesi"]] = s = {
                **t, "nama": t["nama_kegiatan"] or t["nama"], "titik_ids": [], "tingkat_list": [], "hadir": 0
            }  # fmt: skip
        s["titik_ids"].append(t["id"])
        s["tingkat_list"].append(t["tingkat"])
        s["hadir"] += t["hadir"]
        s["id"] = min(s["id"], t["id"])
        # Sesi dianggap berlangsung bila salah satu titiknya terbuka.
        if URUT_KELOMPOK.index(t["kelompok"]) < URUT_KELOMPOK.index(s["kelompok"]):
            s["kelompok"] = t["kelompok"]
        if t["status"] != s["status"]:
            s["status"] = "CAMPURAN"
    for s in sesi.values():
        semua = set(s["tingkat_list"])
        s["tingkat"] = "SEMUA" if "SEMUA" in semua or len(semua) > 1 else s["tingkat_list"][0]
    return list(sesi.values())


@require_GET
@api_peran("PANITIA", "SUPERADMIN")
def daftar_titik(request):
    nilai = pengaturan.semua()
    sekarang = timezone.now()
    hadir = dict(Kehadiran.objects.values_list("titik_absen_id").annotate(n=Count("id")))
    hasil = []
    for t in TitikAbsen.objects.select_related("kegiatan").order_by("tanggal", "mulai", "kode"):
        mulai, akhir = services.jendela_titik(t, nilai)
        hasil.append(
            {
                "id": t.pk,
                "sesi": services.kunci_sesi(t),
                "nama_kegiatan": t.kegiatan.nama if t.kegiatan_id else "",
                "kode": t.kode,
                "nama": t.nama_tampil,
                "tingkat": t.tingkat,
                "tanggal": t.tanggal.isoformat(),
                "mulai": f"{t.mulai:%H.%M}",
                "selesai": f"{t.selesai:%H.%M}" if t.selesai else "selesai",
                "lokasi": t.lokasi,
                "status": t.status,
                "kelompok": services.kelompok_titik(t, sekarang, nilai),
                "terbuka_dari": mulai.isoformat(),
                "terbuka_sampai": akhir.isoformat(),
                "hadir": hadir.get(t.pk, 0),
            }
        )
    return JsonResponse({"sekarang": sekarang.isoformat(), "titik": hasil, "sesi": _sesi_dari_titik(hasil)})


@require_GET
@api_peran("PANITIA", "SUPERADMIN")
def ringkas_titik(request, pk: int):
    """Penghitung untuk layar pindai: jumlah hadir, kontingen hadir, 10 pindaian terakhir (semua HP).

    Mencakup semua titik sesi itu (kegiatan sama, hari sama, semua tingkat)."""
    t = TitikAbsen.objects.filter(pk=pk).first()
    if t is None:
        return JsonResponse({"galat": "TITIK_TIDAK_ADA"}, status=404)
    saudara = services.saudara_titik(t)
    qs = Kehadiran.objects.filter(titik_absen__in=saudara)
    agregat = qs.aggregate(hadir=Count("id"), kontingen=Count("peserta__kontingen", distinct=True))
    terakhir = [
        {
            "nama": k.peserta.nama_lengkap,
            "kontingen": k.peserta.kontingen.kode,
            "jam": f"{timezone.localtime(k.diterima_pada):%H.%M}",
            "oleh": k.nama_pemindai,
        }
        for k in qs.select_related("peserta__kontingen").order_by("-diterima_pada")[:10]
    ]
    return JsonResponse(
        {
            "id": t.pk,
            "terbuka": any(services.titik_terbuka(x) for x in saudara),
            "hadir": agregat["hadir"],
            "kontingen_hadir": agregat["kontingen"],
            "kontingen_total": _jumlah_kontingen(services.tingkat_sesi(saudara)),
            "terakhir": terakhir,
        }
    )


@require_GET
@api_peran("PANITIA", "SUPERADMIN")
def peserta_ringan(request, pk: int):
    """Daftar ringan untuk cache di HP (tampilan nama saat offline). Tanpa data pribadi."""
    t = TitikAbsen.objects.filter(pk=pk).first()
    if t is None:
        return JsonResponse({"galat": "TITIK_TIDAK_ADA"}, status=404)
    qs = Peserta.objects.filter(kartu_aktif=True).exclude(qr_token=None).select_related("kontingen")
    qs = _saring_tingkat(qs, services.tingkat_sesi(services.saudara_titik(t)))
    data = [
        {
            "id": p.pk,
            "h": hash_token(p.qr_token),
            "k": p.kode_kartu,
            "nama": p.nama_lengkap,
            "kontingen": p.kontingen.kode,
            "tingkat": p.tingkat,
            "peran": p.get_peran_display(),
        }
        for p in qs.only("qr_token", "kode_kartu", "nama_lengkap", "tingkat", "peran", "kontingen__kode")
    ]
    return JsonResponse({"titik": t.pk, "peserta": data})


@require_GET
@api_peran("PANITIA", "SUPERADMIN")
def cari_peserta(request):
    """Cari manual (kartu rusak/tertinggal): nama atau kode kartu, hanya tingkat yang sesuai titik."""
    q = " ".join(request.GET.get("q", "").split())[:60]
    t = TitikAbsen.objects.filter(pk=request.GET.get("titik") or 0).first()
    if len(q) < 2 or t is None:
        return JsonResponse({"hasil": []})
    saudara = services.saudara_titik(t)
    qs = _saring_tingkat(
        Peserta.objects.filter(kartu_aktif=True).select_related("kontingen"), services.tingkat_sesi(saudara)
    )
    kode = q.upper().replace(" ", "").replace("-", "")
    filter_kode = Q(kode_kartu=f"{kode[:4]}-{kode[4:8]}") if len(kode) == 8 else Q()
    qs = qs.filter(Q(nama_lengkap__icontains=q) | filter_kode)[:20]
    sudah = set(
        Kehadiran.objects.filter(titik_absen__in=saudara, peserta__in=[p.pk for p in qs]).values_list(
            "peserta_id", flat=True
        )
    )
    return JsonResponse({"hasil": [dict(services.data_peserta(p), sudah_hadir=p.pk in sudah) for p in qs]})


@require_POST
@api_peran("PANITIA", "SUPERADMIN")
def pindai(request):
    data = _json_body(request)
    if data is None:
        return JsonResponse({"galat": "DATA_SALAH", "pesan": "Format data salah."}, status=400)
    try:
        hasil = services.pindai(request.user, data)
    except services.DataTidakValid as e:
        return JsonResponse({"galat": "DATA_SALAH", "pesan": str(e)}, status=400)
    return JsonResponse(hasil.json())


@require_POST
@api_peran("PANITIA", "SUPERADMIN")
def pindai_batch(request):
    """Kirim antrean offline sekaligus (maksimal 50). Setiap item dijawab sendiri-sendiri."""
    data = _json_body(request)
    if not isinstance(data, dict) or not isinstance(data.get("pindaian"), list):
        return JsonResponse({"galat": "DATA_SALAH", "pesan": "Format data salah."}, status=400)
    if len(data["pindaian"]) > BATAS_BATCH:
        return JsonResponse(
            {"galat": "TERLALU_BANYAK", "pesan": f"Maksimal {BATAS_BATCH} pindaian sekali kirim."}, status=400
        )
    hasil = []
    for item in data["pindaian"]:
        try:
            jawab = services.pindai(request.user, item).json()
        except services.DataTidakValid as e:
            jawab = {"status": "GALAT", "kode": "DATA_SALAH", "pesan": str(e)}
        jawab["client_uuid"] = str(item.get("client_uuid", "")) if isinstance(item, dict) else ""
        hasil.append(jawab)
    return JsonResponse({"hasil": hasil})
