"""Superadmin: kelola tiga akun (nama akun, kata sandi, perangkat yang sedang masuk)."""

from __future__ import annotations

from django import forms
from django.contrib import messages
from django.contrib.auth.password_validation import validate_password
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.inti.log import catat

from .decorators import superadmin_wajib
from .models import Pengguna, SesiAkun
from .services import ganti_sandi, keluarkan_semua


class FormSandi(forms.Form):
    sandi_baru = forms.CharField(label="Kata sandi baru", min_length=10, max_length=128,
                                 widget=forms.PasswordInput(attrs={"class": "input", "autocomplete": "new-password"}))  # fmt: skip
    ulangi = forms.CharField(label="Ulangi kata sandi baru", max_length=128,
                             widget=forms.PasswordInput(attrs={"class": "input", "autocomplete": "new-password"}))  # fmt: skip

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        data = super().clean()
        if data.get("sandi_baru") and data.get("ulangi") and data["sandi_baru"] != data["ulangi"]:
            self.add_error("ulangi", "Kata sandi tidak sama.")
        if data.get("sandi_baru"):
            try:
                validate_password(data["sandi_baru"], self.user)
            except forms.ValidationError as e:
                self.add_error("sandi_baru", e)
        return data


class FormNamaAkun(forms.Form):
    username = forms.RegexField(label="Nama akun", regex=r"^[a-zA-Z0-9_.-]{3,30}$", max_length=30,
                                error_messages={"invalid": "3-30 karakter: huruf, angka, titik, garis bawah, tanda hubung."},
                                widget=forms.TextInput(attrs={"class": "input", "autocapitalize": "none"}))  # fmt: skip


@superadmin_wajib
def daftar(request):
    akun = list(Pengguna.objects.order_by("id"))
    for a in akun:
        a.daftar_sesi = list(SesiAkun.objects.filter(pengguna=a).order_by("-login_pada")[:20])
    return render(request, "superadmin/akun.html", {"menu_aktif": "akun", "akun": akun})


@superadmin_wajib
def ubah_sandi(request, pk: int):
    user = get_object_or_404(Pengguna, pk=pk)
    form = FormSandi(request.POST or None, user=user)
    if request.method == "POST" and form.is_valid():
        jumlah = ganti_sandi(request, user, form.cleaned_data["sandi_baru"])
        messages.success(request, f"Kata sandi akun {user.username} diganti. {jumlah} perangkat dikeluarkan.")
        return redirect("akun_admin:daftar")
    return render(request, "superadmin/akun_sandi.html", {"menu_aktif": "akun", "form": form, "u": user})


@superadmin_wajib
def ubah_nama(request, pk: int):
    user = get_object_or_404(Pengguna, pk=pk)
    form = FormNamaAkun(request.POST or None, initial={"username": user.username})
    if request.method == "POST" and form.is_valid():
        baru = form.cleaned_data["username"]
        if Pengguna.objects.filter(username__iexact=baru).exclude(pk=user.pk).exists():
            form.add_error("username", "Nama akun sudah dipakai.")
        else:
            lama = user.username
            user.username = baru
            user.save(update_fields=["username"])
            catat(request, "akun.nama_diubah", user, lama={"username": lama}, baru={"username": baru})
            messages.success(request, f"Nama akun {lama} diganti menjadi {baru}.")
            return redirect("akun_admin:daftar")
    return render(request, "superadmin/akun_nama.html", {"menu_aktif": "akun", "form": form, "u": user})


@superadmin_wajib
@require_POST
def keluarkan(request, pk: int):
    user = get_object_or_404(Pengguna, pk=pk)
    sendiri = user.pk == request.user.pk
    jumlah = keluarkan_semua(user, kecuali_session_key=request.session.session_key if sendiri else None)
    catat(request, "akun.dikeluarkan", user, keterangan=f"{jumlah} perangkat akun {user.username} dikeluarkan")
    messages.success(request, f"{jumlah} perangkat akun {user.username} dikeluarkan.")
    return redirect("akun_admin:daftar")
