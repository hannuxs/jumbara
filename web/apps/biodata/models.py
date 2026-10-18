"""Biodata peserta (satu baris per orang), tanda untuk superadmin, dan token kiriman."""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from apps.inti.models import ModelHapusLunak, Tingkat
from apps.kontingen.models import Kontingen


class Peran(models.TextChoices):
    PESERTA = "PESERTA", "Peserta"
    PIMPINAN_KONTINGEN = "PIMPINAN_KONTINGEN", "Pimpinan Kontingen"
    PEMBINA_PENDAMPING = "PEMBINA_PENDAMPING", "Pembina Pendamping"
    PENINJAU = "PENINJAU", "Peninjau"


PERAN_DEWASA = {Peran.PIMPINAN_KONTINGEN, Peran.PEMBINA_PENDAMPING}


class JenisKelamin(models.TextChoices):
    LAKI_LAKI = "L", "Laki-laki"
    PEREMPUAN = "P", "Perempuan"


class GolonganDarah(models.TextChoices):
    A = "A", "A"
    B = "B", "B"
    AB = "AB", "AB"
    O = "O", "O"  # noqa: E741 (golongan darah O)
    BELUM_TAHU = "BELUM_TAHU", "Belum tahu"


class Sumber(models.TextChoices):
    FORM_PUBLIK = "FORM_PUBLIK", "Form publik"
    SUPERADMIN = "SUPERADMIN", "Superadmin"


class Peserta(ModelHapusLunak):
    """Biodata. NIK disimpan terenkripsi; `nik_hash` (HMAC) dipakai untuk cek dobel."""

    kode_pendaftaran = models.CharField(max_length=12, unique=True)
    kontingen = models.ForeignKey(Kontingen, on_delete=models.PROTECT, related_name="peserta")
    tingkat = models.CharField(max_length=10, choices=Tingkat.choices)
    peran = models.CharField(max_length=20, choices=Peran.choices)

    nama_lengkap = models.CharField(max_length=100, db_index=True)
    nik_terenkripsi = models.TextField(editable=False)
    nik_hash = models.CharField(max_length=64, editable=False)
    nik_samar = models.CharField(max_length=16, editable=False)
    nik_akhir4 = models.CharField(max_length=4, db_index=True, editable=False)
    nomor_induk_anggota = models.CharField(max_length=50, blank=True)
    jenis_kelamin = models.CharField(max_length=1, choices=JenisKelamin.choices)
    tempat_lahir = models.CharField(max_length=60)
    tanggal_lahir = models.DateField()
    alamat = models.TextField(max_length=300)
    golongan_darah = models.CharField(max_length=10, choices=GolonganDarah.choices)
    telepon = models.CharField(max_length=16, blank=True)
    nama_orang_tua = models.CharField(max_length=100, blank=True)
    telepon_orang_tua = models.CharField(max_length=16, blank=True)

    foto_path = models.CharField(max_length=255, blank=True)
    foto_asli_hash = models.CharField(max_length=64, blank=True, db_index=True)
    persetujuan_data_pada = models.DateTimeField(null=True, blank=True)

    # Tahap 2 (kartu). Kolom dibuat sejak awal agar tabel berisi data asli tidak dibongkar.
    qr_token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    kode_kartu = models.CharField(max_length=9, unique=True, null=True, blank=True)
    versi_kartu = models.PositiveSmallIntegerField(default=1)
    kartu_aktif = models.BooleanField(default=True)
    perlu_cetak_ulang = models.BooleanField(default=False)
    # Tahap 5 (piagam).
    tidak_berhak_piagam = models.BooleanField(default=False)
    alasan_tidak_berhak_piagam = models.CharField(max_length=255, blank=True)

    sumber = models.CharField(max_length=20, choices=Sumber.choices, default=Sumber.FORM_PUBLIK)
    ip_pengirim = models.GenericIPAddressField(null=True, blank=True)
    user_agent_pengirim = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "peserta"
        verbose_name_plural = "peserta"
        ordering = ["-dibuat_pada"]
        constraints = [
            models.UniqueConstraint(fields=["nik_hash", "aktif_key"], name="peserta_nik_unik_aktif"),
        ]
        indexes = [models.Index(fields=["kontingen", "tingkat", "peran"])]

    def __str__(self) -> str:
        return f"{self.nama_lengkap} ({self.kode_pendaftaran})"

    @property
    def wajib_data_ortu(self) -> bool:
        return self.peran not in PERAN_DEWASA


class JenisPenanda(models.TextChoices):
    KUOTA_PENUH = "KUOTA_PENUH", "Kuota kontingen sudah penuh"
    TINGKAT_BEDA = "TINGKAT_BEDA", "Tingkat beda dengan kontingen"
    USIA_TIDAK_WAJAR = "USIA_TIDAK_WAJAR", "Usia tidak wajar"
    FOTO_DUPLIKAT = "FOTO_DUPLIKAT", "Foto sama dengan orang lain"
    NAMA_MIRIP = "NAMA_MIRIP", "Nama mirip dalam kontingen"


class PenandaPeserta(models.Model):
    """Tanda otomatis agar superadmin memeriksa. Tidak pernah menolak kiriman."""

    peserta = models.ForeignKey(Peserta, on_delete=models.CASCADE, related_name="penanda")
    jenis = models.CharField(max_length=30, choices=JenisPenanda.choices)
    pesan = models.CharField(max_length=255)
    dibuat_pada = models.DateTimeField(default=timezone.now)
    diabaikan_oleh = models.CharField(max_length=100, blank=True)
    diabaikan_pada = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "tanda peserta"
        verbose_name_plural = "tanda peserta"
        constraints = [
            models.UniqueConstraint(fields=["peserta", "jenis"], name="penanda_unik_per_jenis"),
        ]

    def __str__(self) -> str:
        return f"{self.get_jenis_display()}: {self.pesan}"


class TokenKiriman(models.Model):
    """Token sekali pakai per halaman form agar kiriman ganda tidak membuat dua biodata."""

    nonce = models.CharField(max_length=32, unique=True)
    peserta = models.ForeignKey(Peserta, null=True, blank=True, on_delete=models.SET_NULL)
    dipakai_pada = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "token kiriman"
        verbose_name_plural = "token kiriman"
