"""Kontingen (sekolah) dan kuotanya. Sumber awal: data/kontingen.csv."""

from __future__ import annotations

from django.db import models

from apps.inti.models import ModelHapusLunak, Tingkat


class Kontingen(ModelHapusLunak):
    kode = models.CharField("kode", max_length=10, help_text="Contoh MU-01, MA-01, WI-01")
    nama = models.CharField("nama resmi", max_length=150)
    tingkat = models.CharField("tingkat", max_length=10, choices=Tingkat.choices)
    nama_di_gform = models.CharField("nama di Google Form", max_length=200, blank=True)
    pimpinan_gform = models.CharField("pimpinan (GForm)", max_length=255, blank=True)
    pendamping_gform = models.CharField("pendamping (GForm)", max_length=255, blank=True)
    jumlah_pendamping_tambahan = models.PositiveSmallIntegerField(default=0)
    peserta_inti_gform = models.PositiveSmallIntegerField(default=0)
    peninjau_dihitung = models.PositiveSmallIntegerField(default=0)
    kuota_awal = models.PositiveSmallIntegerField("kuota awal (CSV)", default=0)
    kuota = models.PositiveSmallIntegerField("kuota", default=0)
    kuota_diubah_manual = models.BooleanField(default=False)
    catatan_data = models.TextField("catatan perapian data", blank=True)
    catatan = models.TextField("catatan superadmin", blank=True)
    # Tahap 2 (QR tenda untuk Anjangsana). Dibuat sejak awal agar tabel tidak dibongkar.
    qr_token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    qr_token_dibuat_pada = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "kontingen"
        verbose_name_plural = "kontingen"
        ordering = ["kode"]
        constraints = [
            models.UniqueConstraint(fields=["kode", "aktif_key"], name="kontingen_kode_unik_aktif"),
        ]

    def __str__(self) -> str:
        return self.nama


URUTAN_TINGKAT = models.Case(
    models.When(tingkat=Tingkat.MULA, then=0),
    models.When(tingkat=Tingkat.MADYA, then=1),
    models.When(tingkat=Tingkat.WIRA, then=2),
    default=3,
)
