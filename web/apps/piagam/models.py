"""Template dan penerbitan piagam (docs/18-PIAGAM.md)."""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from apps.biodata.models import Peserta
from apps.inti.models import ModelDasar, ModelHapusLunak
from apps.kontingen.models import Kontingen


class JenisPiagam(models.TextChoices):
    PESERTA = "PESERTA", "Piagam peserta"
    JUARA = "JUARA", "Piagam juara"


class UkuranKertas(models.TextChoices):
    A4 = "A4", "A4 (210 x 297 mm)"
    F4 = "F4", "F4 (215 x 330 mm)"


class Orientasi(models.TextChoices):
    MENDATAR = "MENDATAR", "Mendatar (landscape)"
    TEGAK = "TEGAK", "Tegak (portrait)"


class TemplatePiagam(ModelHapusLunak):
    """Latar (gambar dari panitia, PDF diubah ke gambar) + daftar elemen teks.

    `elemen` (JSON list): {"kode", "teks" (boleh berisi {nama} {kontingen} ...), "x", "y", "lebar" (mm,
    dari kiri atas), "font", "ukuran", "ukuran_min", "warna", "rata" (KIRI/TENGAH/KANAN)}.
    """

    nama = models.CharField(max_length=120)
    jenis = models.CharField(max_length=10, choices=JenisPiagam.choices)
    ukuran_kertas = models.CharField(max_length=4, choices=UkuranKertas.choices, default=UkuranKertas.A4)
    orientasi = models.CharField(max_length=10, choices=Orientasi.choices, default=Orientasi.MENDATAR)
    latar = models.CharField(max_length=255, blank=True, help_text="Nama file gambar latar di folder privat.")
    latar_asli = models.CharField(max_length=255, blank=True)
    desain_bawaan = models.BooleanField(
        default=True, help_text="Gambar bingkai dan judul bawaan SIGAP bila belum ada latar dari panitia."
    )
    tempel_logo = models.BooleanField(
        default=True, help_text="Tempel logo PMI + Jumbara V (matikan bila sudah ada di latar)."
    )
    logo_x = models.FloatField(default=0, help_text="mm dari kiri; 0 = tengah")
    logo_y = models.FloatField(default=12)
    logo_tinggi = models.FloatField(default=22)
    elemen = models.JSONField(default=list, blank=True)
    aktif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "template piagam"
        verbose_name_plural = "template piagam"
        ordering = ["jenis", "nama"]

    def __str__(self) -> str:
        return self.nama


class PiagamTerbit(ModelDasar):
    """Satu piagam yang sudah diberi nomor. PDF dibuat ulang dari `data` setiap diunduh (nomor tetap)."""

    kunci = models.CharField(max_length=80, unique=True, help_text="P:<peserta> atau J:<sumber>:<subjek>")
    jenis = models.CharField(max_length=10, choices=JenisPiagam.choices)
    urut = models.PositiveIntegerField()
    nomor = models.CharField(max_length=120, unique=True)
    template = models.ForeignKey(TemplatePiagam, on_delete=models.PROTECT, related_name="terbit")
    peserta = models.ForeignKey(Peserta, null=True, blank=True, on_delete=models.PROTECT, related_name="piagam")
    kontingen = models.ForeignKey(Kontingen, null=True, blank=True, on_delete=models.PROTECT, related_name="piagam")
    sumber = models.CharField(max_length=80, blank=True, help_text="Untuk juara: form:<id> atau anjangsana:<tingkat>")
    peringkat = models.PositiveSmallIntegerField(null=True, blank=True)
    data = models.JSONField(default=dict)
    diterbitkan_pada = models.DateTimeField(default=timezone.now)
    diterbitkan_oleh = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "piagam terbit"
        verbose_name_plural = "piagam terbit"
        ordering = ["jenis", "urut"]
        constraints = [models.UniqueConstraint(fields=["jenis", "urut"], name="piagam_urut_unik")]

    def __str__(self) -> str:
        return self.nomor
