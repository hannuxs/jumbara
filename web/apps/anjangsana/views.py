"""Halaman publik Anjangsana (tanpa login) dan API alurnya. docs/17-ANJANGSANA.md"""

from __future__ import annotations

import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django_ratelimit.core import is_ratelimited

from . import services as svc

# Banyak HP di lokasi bisa berbagi satu IP operator seluler (CGNAT), jadi batas per IP longgar;
# batas ketat ada per kartu (services.BATAS_KUNJUNGAN_PER_JAM).
BATAS_IP = "240/m"


@ensure_csrf_cookie
def beranda(request):
    st = svc.status()
    return render(request, "anjangsana/beranda.html", {"st": st, "aspek": svc.ASPEK})


def _api(fungsi):
    """POST JSON -> JSON. Galat alur dikembalikan sebagai {ok: false, kode, pesan}."""

    @require_POST
    def _view(request):
        if is_ratelimited(request, group="anjangsana.api", key="ip", rate=BATAS_IP, method="POST", increment=True):
            return JsonResponse(
                {"ok": False, "kode": "TERLALU_SERING", "pesan": "Terlalu banyak percobaan. Tunggu sebentar."},
                status=429,
            )
        try:
            data = json.loads(request.body or b"{}")
            if not isinstance(data, dict):
                raise ValueError
        except ValueError:
            return JsonResponse({"ok": False, "kode": "DATA_SALAH", "pesan": "Data tidak valid."}, status=400)
        try:
            hasil = fungsi(request, data)
        except svc.GagalAnjangsana as e:
            return JsonResponse({"ok": False, "kode": e.kode, "pesan": e.pesan}, status=e.status)
        return JsonResponse({"ok": True, **hasil})

    _view.__name__ = fungsi.__name__
    return _view


def _teks(data: dict, kunci: str, maks: int = 200) -> str:
    nilai = data.get(kunci)
    return str(nilai)[:maks] if isinstance(nilai, (str, int)) else ""


@_api
def api_kartu(request, data):
    return svc.pindai_kartu(_teks(data, "teks"))


@_api
def api_tuan_rumah(request, data):
    return svc.pindai_tuan_rumah(_teks(data, "tiket", 500), _teks(data, "teks"))


@_api
def api_kunjungan(request, data):
    return svc.catat_kunjungan(request, _teks(data, "tiket_tuan", 500))


@_api
def api_review(request, data):
    nilai = data.get("nilai") if isinstance(data.get("nilai"), dict) else {}
    return svc.kirim_review(
        request, _teks(data, "tiket_kunjungan", 500), nilai, _teks(data, "komentar", 600), data.get("ganti") is True
    )
