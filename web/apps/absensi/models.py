"""Kegiatan, kuota, titik absen, dan kehadiran.

Tahap 0 membuat tabelnya (supaya relasi ke peserta sudah benar sejak awal). Halaman pemindai
dan rekap dibuat di Tahap 3 (lihat docs/14-ABSENSI.md).
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from apps.biodata.models import Peserta
from apps.inti.models import ModelDasar, ModelHapusLunak
from apps.kontingen.models import Kontingen


class KelompokKegiatan(models.TextChoices):
    JUMPA = "JUMPA", "Jumpa"
    BAKTI = "BAKTI", "Bakti"
    GEMBIRA = "GEMBIRA", "Gembira"
    ADMINISTRASI = "ADMINISTRASI", "Administrasi"


class TingkatTitik(models.TextChoices):
    MULA = "MULA", "Mula"
    MADYA = "MADYA", "Madya"
    WIRA = "WIRA", "Wira"
    SEMUA = "SEMUA", "Semua tingkat"


class StatusTitik(models.TextChoices):
    OTOMATIS = "OTOMATIS", "Otomatis (ikut jadwal)"
    BUKA = "BUKA", "Buka paksa"
    TUTUP = "TUTUP", "Tutup paksa"


class Metode(models.TextChoices):
    SCAN = "SCAN", "Pindai"
    MANUAL = "MANUAL", "Manual"


class Kegiatan(ModelDasar):
    kode = models.CharField(max_length=40, unique=True)
    nama = models.CharField(max_length=150)
    kelompok = models.CharField(max_length=20, choices=KelompokKegiatan.choices)
    dipisah_per_tingkat = models.BooleanField(default=True)
    kuota_default = models.PositiveSmallIntegerField(null=True, blank=True)
    rincian_kuota = models.CharField(max_length=255, blank=True)
    sistem_penilaian = models.CharField(max_length=100, blank=True)
    catatan = models.TextField(blank=True)
    urutan = models.PositiveSmallIntegerField(default=0)
    bisa_dipilih = models.BooleanField(
        default=True, help_text="Tampil sebagai pilihan kegiatan di form biodata (Daftar Ulang dan Anjangsana tidak)."
    )
    # Bentrok yang ditetapkan panitia walau jam di titik absen tidak bertumpuk (misalnya Traveling yang
    # "08.00-selesai" berlangsung sampai sore sehingga bentrok dengan Got Talent). Berlaku dua arah.
    bentrok_dengan = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=True,
        help_text="Kegiatan yang tidak boleh dipilih bersamaan di form biodata walau jamnya tidak bertumpuk.",
    )

    class Meta:
        verbose_name = "kegiatan"
        verbose_name_plural = "kegiatan"
        ordering = ["urutan", "nama"]

    def __str__(self) -> str:
        return self.nama


class KuotaKegiatan(ModelDasar):
    """Kuota orang per kontingen untuk satu kegiatan. kontingen NULL = berlaku umum."""

    kegiatan = models.ForeignKey(Kegiatan, on_delete=models.CASCADE, related_name="kuota")
    kontingen = models.ForeignKey(Kontingen, null=True, blank=True, on_delete=models.CASCADE)
    kuota = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name = "kuota kegiatan"
        verbose_name_plural = "kuota kegiatan"
        constraints = [
            models.UniqueConstraint(fields=["kegiatan", "kontingen"], name="kuota_kegiatan_unik"),
        ]


class TitikAbsen(ModelDasar):
    """Satu sesi absensi = kegiatan x tingkat x hari/sesi."""

    kode = models.CharField(max_length=20, unique=True)
    kegiatan = models.ForeignKey(Kegiatan, null=True, blank=True, on_delete=models.SET_NULL)
    tingkat = models.CharField(max_length=10, choices=TingkatTitik.choices, default=TingkatTitik.SEMUA)
    nama_tampil = models.CharField(max_length=200)
    tanggal = models.DateField()
    mulai = models.TimeField()
    selesai = models.TimeField(null=True, blank=True)
    lokasi = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=10, choices=StatusTitik.choices, default=StatusTitik.OTOMATIS)
    hitung_poin = models.BooleanField(default=True)
    catatan = models.TextField(blank=True)

    class Meta:
        verbose_name = "titik absen"
        verbose_name_plural = "titik absen"
        ordering = ["tanggal", "mulai", "kode"]
        indexes = [models.Index(fields=["tanggal", "status"])]

    def __str__(self) -> str:
        return f"{self.kode} {self.nama_tampil}"


class Kehadiran(ModelHapusLunak):
    """Satu baris per orang per titik absen (UNIQUE pada data aktif). client_uuid idempoten."""

    titik_absen = models.ForeignKey(TitikAbsen, on_delete=models.PROTECT, related_name="kehadiran")
    peserta = models.ForeignKey(Peserta, on_delete=models.PROTECT, related_name="kehadiran")
    dipindai_pada = models.DateTimeField()
    diterima_pada = models.DateTimeField(default=timezone.now)
    nama_pemindai = models.CharField(max_length=100)
    perangkat_id = models.CharField(max_length=64, blank=True)
    metode = models.CharField(max_length=10, choices=Metode.choices, default=Metode.SCAN)
    client_uuid = models.UUIDField(unique=True)
    offline = models.BooleanField(default=False)
    alasan_manual = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "kehadiran"
        verbose_name_plural = "kehadiran"
        constraints = [
            models.UniqueConstraint(fields=["titik_absen", "peserta", "aktif_key"], name="kehadiran_unik_aktif"),
        ]


class PindaianDitolak(models.Model):
    """Catatan pindaian merah untuk audit."""

    titik_absen = models.ForeignKey(TitikAbsen, null=True, on_delete=models.SET_NULL)
    peserta = models.ForeignKey(Peserta, null=True, blank=True, on_delete=models.SET_NULL)
    kode = models.CharField(max_length=40)
    qr_ringkas = models.CharField(max_length=80, blank=True)
    client_uuid = models.UUIDField(unique=True)
    nama_pemindai = models.CharField(max_length=100, blank=True)
    perangkat_id = models.CharField(max_length=64, blank=True)
    dibuat_pada = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "pindaian ditolak"
        verbose_name_plural = "pindaian ditolak"
