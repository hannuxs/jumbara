"""Sesi mutlak 2 jam sejak login (tidak diperpanjang oleh aktivitas)."""

from __future__ import annotations

import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

KUNCI_LOGIN_PADA = "sigap_login_pada"
PESAN_HABIS = "Sesi Anda sudah 2 jam. Silakan masuk lagi."


def batas_detik() -> int:
    return settings.SIGAP_SESI_MENIT * 60


def sisa_detik(request) -> int | None:
    login_pada = request.session.get(KUNCI_LOGIN_PADA)
    if login_pada is None:
        return None
    return int(login_pada + batas_detik() - time.time())


class SesiMutlakMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            sisa = sisa_detik(request)
            if sisa is None or sisa <= 0:
                from .services import hapus_catatan_sesi

                hapus_catatan_sesi(request.session.session_key)
                logout(request)
                if request.path.startswith("/api/") or request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({"galat": "SESI_HABIS", "pesan": PESAN_HABIS}, status=401)
                messages.warning(request, PESAN_HABIS)
                return redirect(f"{reverse('akun:masuk')}?next={request.get_full_path()}")
        return self.get_response(request)
