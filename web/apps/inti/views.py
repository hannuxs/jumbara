"""Halaman galat ramah dalam Bahasa Indonesia, tanpa jejak teknis."""

from __future__ import annotations

from django.http import HttpResponseServerError, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string


def _json(request) -> bool:
    return request.path.startswith("/api/") or request.headers.get("x-requested-with") == "XMLHttpRequest"


def terlalu_banyak(request, exception=None):
    pesan = "Terlalu banyak percobaan dalam waktu singkat. Tunggu sebentar lalu coba lagi."
    if _json(request):
        return JsonResponse({"galat": "TERLALU_BANYAK", "pesan": pesan}, status=429)
    return render(request, "galat/galat.html", {"judul": "Tunggu sebentar", "pesan": pesan}, status=429)


def csrf_gagal(request, reason=""):
    pesan = "Halaman sudah terlalu lama terbuka atau cookie diblokir. Muat ulang halaman lalu coba lagi."
    if _json(request):
        return JsonResponse({"galat": "CSRF", "pesan": pesan}, status=403)
    return render(request, "galat/galat.html", {"judul": "Muat ulang halaman", "pesan": pesan}, status=403)


def galat_400(request, exception=None):
    return render(
        request,
        "galat/galat.html",
        {"judul": "Permintaan tidak valid", "pesan": "Periksa alamat lalu coba lagi."},
        status=400,
    )


def galat_403(request, exception=None):
    pesan = "Anda tidak punya akses ke halaman ini."
    if _json(request):
        return JsonResponse({"galat": "DILARANG", "pesan": pesan}, status=403)
    return render(request, "galat/galat.html", {"judul": "Tidak ada akses", "pesan": pesan}, status=403)


def galat_404(request, exception=None):
    return render(
        request,
        "galat/galat.html",
        {"judul": "Halaman tidak ditemukan", "pesan": "Alamat yang Anda buka tidak ada atau sudah dipindah."},
        status=404,
    )


def galat_500(request):
    # Tanpa context processor (bisa saja database sedang bermasalah).
    isi = render_to_string(
        "galat/galat.html",
        {
            "judul": "Terjadi gangguan",
            "pesan": "Maaf, ada gangguan di server. Coba lagi beberapa saat lagi. Jika terus terjadi, hubungi superadmin.",
        },
    )
    return HttpResponseServerError(isi)
