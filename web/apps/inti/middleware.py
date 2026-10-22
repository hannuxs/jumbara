"""Middleware umum: nama pelaku per perangkat, mode perawatan, header keamanan (CSP)."""

from __future__ import annotations

import re
from urllib.parse import unquote

from django.shortcuts import render

from . import pengaturan

POLA_PERANGKAT = re.compile(r"^[A-Za-z0-9-]{8,64}$")


def _bersihkan_nama(teks: str) -> str:
    teks = unquote(teks or "")
    teks = "".join(c for c in teks if c.isprintable())
    return " ".join(teks.split())[:100]


class PelakuMiddleware:
    """Membaca nama pelaku dan id perangkat dari cookie yang ditulis JavaScript.

    Akun bersama dipakai banyak orang, jadi setiap perangkat menyimpan nama pemakainya.
    Nama ini hanya label untuk log, bukan pengganti login.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.nama_pelaku = _bersihkan_nama(request.COOKIES.get("sigap_nama", ""))
        perangkat = request.COOKIES.get("sigap_perangkat", "")
        request.perangkat_id = perangkat if POLA_PERANGKAT.match(perangkat) else ""
        return self.get_response(request)


JALUR_BEBAS_PERAWATAN = ("/static/", "/masuk/", "/keluar/", "/favicon.ico")


class PerawatanMiddleware:
    """Saat `sistem.perawatan` aktif, semua orang kecuali superadmin melihat halaman perawatan."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith(JALUR_BEBAS_PERAWATAN):
            user = getattr(request, "user", None)
            superadmin = bool(user and user.is_authenticated and getattr(user, "superadmin", False))
            if not superadmin and pengaturan.untuk_request(request).get("sistem.perawatan"):
                return render(request, "galat/perawatan.html", status=503)
        return self.get_response(request)


CSP = "; ".join(
    [
        "default-src 'self'",
        # Alpine.js versi standar membutuhkan 'unsafe-eval' untuk ekspresi di atribut HTML.
        "script-src 'self' 'unsafe-eval'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self'",
        "connect-src 'self'",
        "media-src 'self' blob:",
        "worker-src 'self' blob:",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)


class HeaderKeamananMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("Content-Security-Policy", CSP)
        response.setdefault("Permissions-Policy", "camera=(self), microphone=(), geolocation=()")
        if request.is_secure():
            # Browser mengabaikan (dan memberi peringatan) header ini di HTTP biasa, misalnya uji lewat IP laptop.
            response.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            # Halaman berisi data pribadi tidak boleh disimpan di cache browser/proxy.
            response.setdefault("Cache-Control", "no-store, private")
        return response
