"""Model dasar: waktu dibuat/diubah, soft delete, pengaturan aplikasi, dan log aktivitas."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class Tingkat(models.TextChoices):
    MULA = "MULA", "Mula"
    MADYA = "MADYA", "Madya"
    WIRA = "WIRA", "Wira"


class ModelDasar(models.Model):
    """Kolom waktu yang dipakai semua model domain."""

    dibuat_pada = models.DateTimeField("dibuat pada", default=timezone.now, editable=False)
    diubah_pada = models.DateTimeField("diubah pada", auto_now=True)

    class Meta:
        abstract = True


class ManagerAktif(models.Manager):
    """Manager bawaan: hanya data yang belum dihapus (bukan di tempat sampah)."""

    def get_queryset(self):
        return super().get_queryset().filter(dihapus_pada__isnull=True)


class ModelHapusLunak(ModelDasar):
    """Soft delete. `objects` menyaring data terhapus, `semua` untuk tempat sampah.

    `aktif_key` bernilai 1 untuk data aktif dan NULL untuk data terhapus, sehingga kunci
    UNIQUE (kolom, aktif_key) hanya berlaku pada data aktif (MariaDB tidak punya partial index,
    dan NULL boleh dobel di UNIQUE).
    """

    dihapus_pada = models.DateTimeField("dihapus pada", null=True, blank=True, db_index=True)
    dihapus_oleh = models.CharField("dihapus oleh", max_length=100, blank=True)
    aktif_key = models.PositiveSmallIntegerField(default=1, null=True, editable=False)

    objects = ManagerAktif()
    semua = models.Manager()

    class Meta:
        abstract = True

    @property
    def terhapus(self) -> bool:
        return self.dihapus_pada is not None

    def hapus_lunak(self, oleh: str = "") -> None:
        self.dihapus_pada = timezone.now()
        self.dihapus_oleh = oleh[:100]
        self.aktif_key = None
        self.save(update_fields=["dihapus_pada", "dihapus_oleh", "aktif_key", "diubah_pada"])

    def pulihkan(self) -> None:
        self.dihapus_pada = None
        self.dihapus_oleh = ""
        self.aktif_key = 1
        self.save(update_fields=["dihapus_pada", "dihapus_oleh", "aktif_key", "diubah_pada"])


class Pengaturan(models.Model):
    """Pengaturan yang bisa diubah superadmin (jadwal form, kontak, sakelar)."""

    kunci = models.CharField(max_length=100, unique=True)
    nilai = models.JSONField(null=True, blank=True)
    diubah_pada = models.DateTimeField(auto_now=True)
    diubah_oleh = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "pengaturan"
        verbose_name_plural = "pengaturan"
        ordering = ["kunci"]

    def __str__(self) -> str:
        return self.kunci


class LogAktivitas(models.Model):
    """Riwayat setiap perubahan data. Tidak bisa dihapus dari aplikasi.

    Jangan menyimpan NIK utuh, kata sandi, token, atau foto di sini.
    """

    dibuat_pada = models.DateTimeField(default=timezone.now, db_index=True)
    pengguna = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    peran = models.CharField(max_length=20, blank=True)
    nama_pelaku = models.CharField(max_length=100, blank=True)
    aksi = models.CharField(max_length=50, db_index=True)
    subjek_tipe = models.CharField(max_length=50, blank=True)
    subjek_id = models.CharField(max_length=50, blank=True)
    keterangan = models.CharField(max_length=255, blank=True)
    data_lama = models.JSONField(null=True, blank=True)
    data_baru = models.JSONField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    perangkat_id = models.CharField(max_length=64, blank=True)

    class Meta:
        verbose_name = "log aktivitas"
        verbose_name_plural = "log aktivitas"
        ordering = ["-dibuat_pada", "-id"]
        indexes = [models.Index(fields=["subjek_tipe", "subjek_id"])]

    def __str__(self) -> str:
        return f"{self.dibuat_pada:%Y-%m-%d %H:%M} {self.aksi}"
