"""Riwayat kartu peserta (Tahap 2). Token lama yang dipindai menghasilkan status merah."""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from apps.biodata.models import Peserta


class AlasanKartu(models.TextChoices):
    HILANG = "HILANG", "Hilang"
    RUSAK = "RUSAK", "Rusak"
    DATA_BERUBAH = "DATA_BERUBAH", "Data berubah"
    LAINNYA = "LAINNYA", "Lainnya"


class KartuRiwayat(models.Model):
    peserta = models.ForeignKey(Peserta, on_delete=models.CASCADE, related_name="riwayat_kartu")
    versi = models.PositiveSmallIntegerField()
    qr_token_lama = models.CharField(max_length=64, unique=True)
    kode_kartu_lama = models.CharField(max_length=9, blank=True)
    alasan = models.CharField(max_length=20, choices=AlasanKartu.choices)
    oleh = models.CharField(max_length=100, blank=True)
    dibuat_pada = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "riwayat kartu"
        verbose_name_plural = "riwayat kartu"
