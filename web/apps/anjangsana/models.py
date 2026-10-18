"""Anjangsana: sesi, kunjungan, dan review (Tahap 3, lihat docs/17-ANJANGSANA.md)."""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from apps.biodata.models import Peserta
from apps.inti.models import ModelDasar, ModelHapusLunak
from apps.kontingen.models import Kontingen


class SesiAnjangsana(ModelDasar):
    tanggal = models.DateField()
    mulai = models.TimeField()
    selesai = models.TimeField()

    class Meta:
        verbose_name = "sesi Anjangsana"
        verbose_name_plural = "sesi Anjangsana"
        ordering = ["tanggal", "mulai"]
        constraints = [
            models.UniqueConstraint(fields=["tanggal", "mulai"], name="sesi_anjangsana_unik"),
        ]

    def __str__(self) -> str:
        return f"{self.tanggal} {self.mulai:%H.%M}-{self.selesai:%H.%M}"


class Kunjungan(models.Model):
    pengunjung = models.ForeignKey(Peserta, on_delete=models.PROTECT, related_name="kunjungan")
    kontingen_tamu = models.ForeignKey(Kontingen, on_delete=models.PROTECT, related_name="+")
    kontingen_tuan_rumah = models.ForeignKey(Kontingen, on_delete=models.PROTECT, related_name="+")
    sesi = models.ForeignKey(SesiAnjangsana, null=True, on_delete=models.SET_NULL)
    dipindai_pada = models.DateTimeField(default=timezone.now)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "kunjungan Anjangsana"
        verbose_name_plural = "kunjungan Anjangsana"


class Review(ModelHapusLunak):
    kontingen_tamu = models.ForeignKey(Kontingen, on_delete=models.PROTECT, related_name="+")
    kontingen_tuan_rumah = models.ForeignKey(Kontingen, on_delete=models.PROTECT, related_name="+")
    pengunjung = models.ForeignKey(Peserta, null=True, on_delete=models.SET_NULL)
    nilai_pengetahuan = models.PositiveSmallIntegerField()
    nilai_keterampilan = models.PositiveSmallIntegerField()
    nilai_sikap = models.PositiveSmallIntegerField()
    komentar = models.TextField(blank=True)
    dikirim_pada = models.DateTimeField(default=timezone.now)
    riwayat = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = "review Anjangsana"
        verbose_name_plural = "review Anjangsana"
        constraints = [
            models.UniqueConstraint(
                fields=["kontingen_tamu", "kontingen_tuan_rumah", "aktif_key"],
                name="review_unik_per_pasangan",
            ),
        ]
