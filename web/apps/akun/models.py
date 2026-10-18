"""Tiga akun bersama (superadmin, panitia, juri) dan catatan sesi per perangkat."""

from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Peran(models.TextChoices):
    SUPERADMIN = "SUPERADMIN", "Superadmin"
    PANITIA = "PANITIA", "Panitia"
    JURI = "JURI", "Juri"


class Pengguna(AbstractUser):
    """Model pengguna kustom. Hanya ada tiga baris (satu per peran)."""

    peran = models.CharField(max_length=20, choices=Peran.choices, unique=True)
    sandi_diganti_pada = models.DateTimeField(null=True, blank=True)
    wajib_ganti_sandi = models.BooleanField(
        default=True, help_text="True sampai kata sandi awal diganti dari menu Akun."
    )

    class Meta:
        verbose_name = "akun"
        verbose_name_plural = "akun"

    @property
    def superadmin(self) -> bool:
        return self.peran == Peran.SUPERADMIN

    @property
    def panitia(self) -> bool:
        return self.peran == Peran.PANITIA

    @property
    def juri(self) -> bool:
        return self.peran == Peran.JURI


class SesiAkun(models.Model):
    """Pemetaan akun -> session_key, agar semua perangkat bisa dikeluarkan saat sandi diganti."""

    pengguna = models.ForeignKey(Pengguna, on_delete=models.CASCADE, related_name="sesi")
    session_key = models.CharField(max_length=40, unique=True)
    login_pada = models.DateTimeField(default=timezone.now)
    perangkat_id = models.CharField(max_length=64, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "sesi akun"
        verbose_name_plural = "sesi akun"
        ordering = ["-login_pada"]

    def __str__(self) -> str:
        return f"{self.pengguna} {self.login_pada:%Y-%m-%d %H:%M}"
