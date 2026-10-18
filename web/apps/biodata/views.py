"""Halaman publik: beranda, form biodata, bukti pendaftaran."""

from __future__ import annotations

import logging

from django.core import signing
from django.db import IntegrityError, transaction
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django_ratelimit.core import is_ratelimited

from apps.inti import pengaturan
from apps.inti.utils import tautan_wa

from . import pdf, services
from .forms import PENJELASAN_PERAN, BiodataForm, baca_token, buat_token
from .models import Peserta, Sumber, TokenKiriman

logger = logging.getLogger("sigap")

SALT_BUKTI = "sigap.biodata.bukti"
UMUR_BUKTI = 7 * 24 * 3600
# Batas kiriman BERHASIL per IP. Longgar karena satu sekolah/operator seluler bisa berbagi IP.
BATAS_KIRIM = "30/10m"
BATAS_NIK_DOBEL = "5/m"


def _ajax(request) -> bool:
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def tautan_bukti(peserta: Peserta) -> str:
    token = signing.dumps(peserta.pk, salt=SALT_BUKTI)
    return reverse("biodata:bukti", args=[token])


def _peserta_dari_bukti(token: str) -> Peserta:
    try:
        pk = signing.loads(token, salt=SALT_BUKTI, max_age=UMUR_BUKTI)
    except signing.BadSignature:
        raise Http404 from None
    peserta = Peserta.objects.select_related("kontingen").filter(pk=pk).first()
    if peserta is None:
        raise Http404
    return peserta


def beranda(request):
    nilai = pengaturan.untuk_request(request)
    status = services.status_form(nilai)
    return render(request, "biodata/beranda.html", {"status": status})


def _konteks_form(request, form, status, peringatan_umum=None):
    nilai = pengaturan.untuk_request(request)
    wa = nilai.get("kontak.superadmin_wa", "")
    return {
        "form": form,
        "status": status,
        "penjelasan_peran": PENJELASAN_PERAN,
        "foto_wajib": bool(nilai.get("biodata.foto_wajib", True)),
        "peringatan_umum": peringatan_umum or [],
        "tautan_wa_sekolah": tautan_wa(
            wa, "Halo Superadmin, sekolah saya tidak ada di daftar form biodata SIGAP JUMBARA."
        ),
        "tautan_wa_nik": tautan_wa(wa, "Halo Superadmin, NIK saya sudah terdaftar di form biodata SIGAP JUMBARA."),
    }


def _tolak(request, form, status, pesan: str, kode_status: int = 400, token_baru: str = ""):
    if _ajax(request):
        data = {"ok": False, "umum": [pesan], "galat": {}}
        if token_baru:
            data["token"] = token_baru
        return JsonResponse(data, status=kode_status)
    return render(request, "biodata/form.html", _konteks_form(request, form, status, [pesan]), status=kode_status)


@require_http_methods(["GET", "POST"])
def daftar(request):
    nilai = pengaturan.untuk_request(request)
    status = services.status_form(nilai)
    foto_wajib = bool(nilai.get("biodata.foto_wajib", True))

    if request.method == "GET":
        if not status.terbuka:
            return render(request, "biodata/tutup.html", {"status": status})
        form = BiodataForm(foto_wajib=foto_wajib, initial={"token": buat_token()})
        return render(request, "biodata/form.html", _konteks_form(request, form, status))

    # --- POST ----------------------------------------------------------------
    if not status.terbuka:
        pesan = "Pendaftaran biodata sedang ditutup. Isian Anda tetap tersimpan di HP ini."
        if _ajax(request):
            return JsonResponse({"ok": False, "tutup": True, "umum": [pesan], "galat": {}}, status=403)
        return render(request, "biodata/tutup.html", {"status": status}, status=403)

    if is_ratelimited(request, group="biodata.kirim", key="ip", rate=BATAS_KIRIM, method="POST", increment=False):
        return _tolak(request, BiodataForm(request.POST, foto_wajib=foto_wajib), status,
                      "Terlalu banyak kiriman dari jaringan ini. Tunggu 10 menit lalu coba lagi.", 429)  # fmt: skip

    form = BiodataForm(request.POST, request.FILES, foto_wajib=foto_wajib)

    token = baca_token(request.POST.get("token", ""))
    if token is None:
        data = request.POST.copy()
        data["token"] = buat_token()
        form = BiodataForm(data, foto_wajib=foto_wajib)
        return _tolak(request, form, status, "Halaman sudah terlalu lama terbuka. Periksa isian lalu tekan Kirim sekali lagi.",
                      token_baru=data["token"])  # fmt: skip
    nonce, umur_detik = token

    sudah = TokenKiriman.objects.filter(nonce=nonce).select_related("peserta").first()
    if sudah and sudah.peserta_id:
        # Kiriman ganda (tombol ditekan dua kali / koneksi putus lalu kirim ulang).
        url = tautan_bukti(sudah.peserta)
        return JsonResponse({"ok": True, "url": url}) if _ajax(request) else redirect(url)

    if umur_detik < int(nilai.get("biodata.waktu_minimal_detik", 10) or 0):
        return _tolak(request, form, status, "Mohon periksa kembali isian Anda, lalu tekan Kirim.")

    if not form.is_valid():
        if form.nik_dobel and is_ratelimited(
            request, group="biodata.nik_dobel", key="ip", rate=BATAS_NIK_DOBEL, method="POST", increment=True
        ):
            return _tolak(request, form, status, "Terlalu banyak percobaan. Tunggu 1 menit lalu coba lagi.", 429)
        if _ajax(request):
            galat = {
                nama: [str(e) for e in daftar_galat] for nama, daftar_galat in form.errors.items() if nama != "__all__"
            }
            return JsonResponse(
                {
                    "ok": False,
                    "galat": galat,
                    "umum": [str(e) for e in form.non_field_errors()],
                    "nik_dobel": form.nik_dobel,
                },
                status=400,
            )
        return render(request, "biodata/form.html", _konteks_form(request, form, status), status=400)

    try:
        with transaction.atomic():
            catatan_token = TokenKiriman.objects.create(nonce=nonce)
            peserta = services.buat_peserta(request, form.cleaned_data, form.hasil_foto, Sumber.FORM_PUBLIK)
            catatan_token.peserta = peserta
            catatan_token.save(update_fields=["peserta"])
    except services.NikSudahTerdaftar:
        form.add_error(
            "nik",
            "NIK ini sudah terdaftar. Jika Anda merasa belum pernah mengisi atau ingin memperbaiki data, hubungi superadmin.",
        )
        form.nik_dobel = True
        if _ajax(request):
            return JsonResponse(
                {"ok": False, "galat": {"nik": form.errors["nik"]}, "umum": [], "nik_dobel": True}, status=400
            )
        return render(request, "biodata/form.html", _konteks_form(request, form, status), status=400)
    except IntegrityError:
        # Token yang sama sedang/sudah diproses oleh permintaan lain (kiriman ganda bersamaan).
        sudah = TokenKiriman.objects.filter(nonce=nonce).select_related("peserta").first()
        if sudah and sudah.peserta_id:
            url = tautan_bukti(sudah.peserta)
            return JsonResponse({"ok": True, "url": url}) if _ajax(request) else redirect(url)
        logger.exception("Gagal menyimpan biodata")
        return _tolak(request, form, status, "Gagal menyimpan. Coba tekan Kirim sekali lagi.", 500)

    is_ratelimited(request, group="biodata.kirim", key="ip", rate=BATAS_KIRIM, method="POST", increment=True)
    url = tautan_bukti(peserta)
    if _ajax(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)


def bukti(request, token: str):
    peserta = _peserta_dari_bukti(token)
    return render(request, "biodata/bukti.html", {"peserta": peserta, "token": token})


def bukti_pdf(request, token: str):
    peserta = _peserta_dari_bukti(token)
    isi = pdf.bukti_pendaftaran(peserta)
    respons = HttpResponse(isi, content_type="application/pdf")
    respons["Content-Disposition"] = f'attachment; filename="Bukti_{peserta.kode_pendaftaran}.pdf"'
    return respons


def status_json(request):
    """Status form untuk hitung mundur di beranda (tanpa data pribadi)."""
    status = services.status_form(pengaturan.untuk_request(request))
    return JsonResponse(
        {
            "terbuka": status.terbuka,
            "alasan": status.alasan,
            "sekarang": timezone.now().isoformat(),
            "buka_pada": status.buka_pada.isoformat() if status.buka_pada else None,
        }
    )
