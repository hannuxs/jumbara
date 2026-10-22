"""Masuk, keluar, dan halaman perantara setelah masuk (kembali ke menu terakhir)."""

from __future__ import annotations

from urllib.parse import urlencode

from django import forms
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods, require_POST
from django_ratelimit.core import is_ratelimited

from apps.inti.log import catat
from apps.inti.utils import ip_klien

from .decorators import peran_wajib
from .services import AWALAN_RUTE, HALAMAN_AWAL, catat_login, hapus_catatan_sesi

PESAN_GAGAL = "Nama akun atau kata sandi salah."


class FormMasuk(forms.Form):
    username = forms.CharField(label="Nama akun", max_length=150)
    password = forms.CharField(label="Kata sandi", max_length=128, widget=forms.PasswordInput)


def kunci_masuk(group, request) -> str:
    """Batas percobaan per IP + nama akun."""
    return f"{ip_klien(request)}:{request.POST.get('username', '').strip().lower()[:50]}"


def _next_aman(request, nilai: str) -> str:
    if nilai and url_has_allowed_host_and_scheme(
        nilai, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return nilai
    return ""


@never_cache
@csrf_protect
@require_http_methods(["GET", "POST"])
def masuk(request):
    if request.user.is_authenticated:
        return redirect("akun:lanjut")
    next_url = _next_aman(request, request.POST.get("next") or request.GET.get("next", ""))
    form = FormMasuk(request.POST or None)
    galat = ""
    if request.method == "POST":
        if is_ratelimited(request, group="akun.masuk", key=kunci_masuk, rate="5/m", method="POST", increment=True):
            galat = "Terlalu banyak percobaan. Tunggu 1 menit lalu coba lagi."
        elif form.is_valid():
            user = authenticate(
                request, username=form.cleaned_data["username"].strip(), password=form.cleaned_data["password"]
            )
            if user is not None and user.is_active:
                login(request, user)
                catat_login(request, user)
                tujuan = reverse("akun:lanjut")
                return redirect(f"{tujuan}?{urlencode({'next': next_url})}" if next_url else tujuan)
            catat(
                request,
                "akun.gagal_masuk",
                keterangan=f"Gagal masuk dengan nama akun '{form.cleaned_data['username'][:40]}'",
            )
            galat = PESAN_GAGAL
        else:
            galat = "Isi nama akun dan kata sandi."
    return render(
        request,
        "akun/masuk.html",
        {"form": form, "galat": galat, "next": next_url},
        status=429 if "Terlalu" in galat else 200,
    )


@require_POST
def keluar(request):
    if request.user.is_authenticated:
        catat(request, "akun.keluar", request.user)
        hapus_catatan_sesi(request.session.session_key)
    logout(request)
    return redirect("akun:masuk")


@never_cache
@peran_wajib("SUPERADMIN", "PANITIA", "JURI")
def lanjut(request):
    """Halaman perantara: JavaScript membaca menu terakhir di perangkat ini lalu mengarahkan."""
    peran = request.user.peran
    return render(
        request,
        "akun/lanjut.html",
        {
            "halaman_awal": HALAMAN_AWAL[peran],
            "awalan": AWALAN_RUTE[peran],
            "next": _next_aman(request, request.GET.get("next", "")),
            "minta_nama": peran == "SUPERADMIN",
        },
    )


@peran_wajib("PANITIA", "SUPERADMIN")
def panitia_awal(request):
    """Halaman pemindai kehadiran (docs/14-ABSENSI.md)."""
    return render(request, "panitia/pindai.html")


@peran_wajib("JURI", "SUPERADMIN")
def juri_awal(request):
    return render(request, "akun/segera.html", {"judul": "Form penilaian juri", "tahap": "Tahap 4 (7 November 2026)"})
