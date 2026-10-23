"""Form builder mode 1 (input) dan mode 2 (penilaian). docs/16-FORM-BUILDER.md

Isian setiap kiriman disimpan sebagai JSON {kode_kolom: nilai} agar form bisa diubah superadmin tanpa
migrasi database. Ekspor Excel memakai kode kolom sebagai kepala sehingga data tetap rapi.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.absensi.models import Kegiatan
from apps.biodata.models import Peserta
from apps.inti.models import ModelDasar, ModelHapusLunak
from apps.kontingen.models import Kontingen


class ModeForm(models.TextChoices):
    INPUT = "INPUT", "Mode 1: input biasa"
    PENILAIAN = "PENILAIAN", "Mode 2: penilaian"


class StatusForm(models.TextChoices):
    DRAF = "DRAF", "Draf"
    AKTIF = "AKTIF", "Aktif"
    ARSIP = "ARSIP", "Arsip"


class AksesForm(models.TextChoices):
    SUPERADMIN = "SUPERADMIN", "Hanya superadmin"
    JURI = "JURI", "Juri (ditugaskan)"
    PUBLIK = "PUBLIK", "Publik dengan link"


class JenisSubjek(models.TextChoices):
    KONTINGEN = "KONTINGEN", "Per kontingen"
    PESERTA = "PESERTA", "Per orang"
    BEBAS = "BEBAS", "Tanpa subjek"


class TingkatForm(models.TextChoices):
    MULA = "MULA", "Mula"
    MADYA = "MADYA", "Madya"
    WIRA = "WIRA", "Wira"
    SEMUA = "SEMUA", "Semua tingkat"


class JenisPenilaian(models.TextChoices):
    BIASA = "BIASA", "Biasa (nilai aspek)"
    GUGUR = "GUGUR", "Gugur (isi peringkat akhir)"


class Agregasi(models.TextChoices):
    RATA = "RATA", "Rata-rata antarjuri"
    JUMLAH = "JUMLAH", "Jumlah antarjuri"
    TERAKHIR = "TERAKHIR", "Kiriman terakhir"


class ArahUrut(models.TextChoices):
    TURUN = "TURUN", "Terbesar menjadi juara"
    NAIK = "NAIK", "Terkecil menjadi juara"


class Formulir(ModelHapusLunak):
    slug = models.SlugField(max_length=80)
    # Kunci bersama untuk form yang sama di tingkat berbeda (misal "penilaian-traveling"); dipakai REF.
    kunci_ref = models.SlugField(max_length=80, blank=True)
    judul = models.CharField(max_length=200)
    deskripsi = models.TextField(blank=True)
    mode = models.CharField(max_length=10, choices=ModeForm.choices, default=ModeForm.INPUT)
    status = models.CharField(max_length=10, choices=StatusForm.choices, default=StatusForm.DRAF)
    akses = models.CharField(max_length=12, choices=AksesForm.choices, default=AksesForm.SUPERADMIN)
    buka_pada = models.DateTimeField(null=True, blank=True)
    tutup_pada = models.DateTimeField(null=True, blank=True)
    satu_per_subjek = models.BooleanField(default=False, help_text="Mode 1: satu kiriman per subjek.")
    jenis_subjek = models.CharField(max_length=10, choices=JenisSubjek.choices, default=JenisSubjek.BEBAS)
    kegiatan = models.ForeignKey(Kegiatan, null=True, blank=True, on_delete=models.SET_NULL)
    tingkat = models.CharField(max_length=10, choices=TingkatForm.choices, default=TingkatForm.SEMUA)
    cabang = models.CharField(max_length=80, blank=True)
    jenis_penilaian = models.CharField(max_length=10, choices=JenisPenilaian.choices, default=JenisPenilaian.BIASA)
    agregasi = models.CharField(max_length=10, choices=Agregasi.choices, default=Agregasi.RATA)
    jumlah_juri = models.PositiveSmallIntegerField(
        default=1, help_text="Target juri per subjek (penanda belum lengkap)."
    )
    subjek_kontingen = models.ManyToManyField(Kontingen, blank=True, related_name="+")
    subjek_peserta = models.ManyToManyField(Peserta, blank=True, related_name="+")
    kolom_urut = models.CharField(max_length=40, blank=True)
    arah_urut = models.CharField(max_length=5, choices=ArahUrut.choices, default=ArahUrut.TURUN)
    juri_lihat_hasil = models.BooleanField(default=False)
    terkunci = models.BooleanField(default=False)
    terkunci_pada = models.DateTimeField(null=True, blank=True)
    terkunci_oleh = models.CharField(max_length=100, blank=True)
    perlu_konfirmasi = models.BooleanField(default=False, help_text="Template: aspek/bobot belum final.")
    catatan = models.TextField(blank=True)

    class Meta:
        verbose_name = "form"
        verbose_name_plural = "form"
        ordering = ["judul"]
        constraints = [models.UniqueConstraint(fields=["slug", "aktif_key"], name="formulir_slug_unik")]

    def __str__(self) -> str:
        return self.judul

    @property
    def penilaian(self) -> bool:
        return self.mode == ModeForm.PENILAIAN

    def terbuka(self, pada=None) -> bool:
        """Bisa diisi: aktif, tidak dikunci, dan dalam jadwal (bila diisi)."""
        pada = pada or timezone.now()
        if self.status != StatusForm.AKTIF or self.terkunci:
            return False
        if self.buka_pada and pada < self.buka_pada:
            return False
        return not (self.tutup_pada and pada > self.tutup_pada)


class JenisKolom(models.TextChoices):
    TEKS = "TEKS", "Teks pendek"
    PARAGRAF = "PARAGRAF", "Paragraf"
    ANGKA = "ANGKA", "Angka"
    PILIHAN = "PILIHAN", "Pilihan tunggal (tombol)"
    DROPDOWN = "DROPDOWN", "Pilihan tunggal (daftar)"
    CENTANG = "CENTANG", "Pilihan ganda (centang)"
    TANGGAL = "TANGGAL", "Tanggal"
    JAM = "JAM", "Jam"
    YA_TIDAK = "YA_TIDAK", "Ya/Tidak"
    BERKAS = "BERKAS", "Unggah file"
    SKALA = "SKALA", "Skala 1-5"
    JUDUL = "JUDUL", "Judul bagian / keterangan"
    OTOMATIS = "OTOMATIS", "Otomatis (dari sistem)"
    RUMUS = "RUMUS", "Rumus"
    PERINGKAT = "PERINGKAT", "Peringkat"


JENIS_INPUT = {
    JenisKolom.TEKS, JenisKolom.PARAGRAF, JenisKolom.ANGKA, JenisKolom.PILIHAN, JenisKolom.DROPDOWN,
    JenisKolom.CENTANG, JenisKolom.TANGGAL, JenisKolom.JAM, JenisKolom.YA_TIDAK, JenisKolom.BERKAS, JenisKolom.SKALA,
}  # fmt: skip
JENIS_ANGKA = {JenisKolom.ANGKA, JenisKolom.SKALA, JenisKolom.YA_TIDAK}
JENIS_HITUNG = {JenisKolom.OTOMATIS, JenisKolom.RUMUS, JenisKolom.PERINGKAT}


class SumberOtomatis(models.TextChoices):
    POIN_KEHADIRAN = "poin_kehadiran", "Poin kehadiran kegiatan"
    JUMLAH_HADIR = "jumlah_hadir", "Jumlah hadir kegiatan"
    KUOTA = "kuota", "Kuota kegiatan"
    JUMLAH_JURI = "jumlah_juri", "Jumlah juri yang menilai"


class Kolom(ModelDasar):
    """Satu isian/kolom. `pengaturan` (JSON): min, max, desimal, pilihan, rumus, sumber, dasar, arah,
    tipe_berkas, ukuran_mb, tampil_desimal."""

    formulir = models.ForeignKey(Formulir, on_delete=models.CASCADE, related_name="kolom")
    kode = models.CharField(max_length=40)
    label = models.CharField(max_length=200)
    bantuan = models.CharField(max_length=300, blank=True)
    jenis = models.CharField(max_length=10, choices=JenisKolom.choices)
    wajib = models.BooleanField(default=False)
    urutan = models.PositiveIntegerField(default=0)
    pengaturan = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "kolom"
        verbose_name_plural = "kolom"
        ordering = ["urutan", "id"]
        constraints = [models.UniqueConstraint(fields=["formulir", "kode"], name="kolom_kode_unik")]

    def __str__(self) -> str:
        return f"{self.label} [{self.kode}]"

    @property
    def diisi(self) -> bool:
        return self.jenis in JENIS_INPUT

    @property
    def dihitung(self) -> bool:
        return self.jenis in JENIS_HITUNG

    def atur(self, kunci: str, bawaan=None):
        return (self.pengaturan or {}).get(kunci, bawaan)


class Kiriman(ModelHapusLunak):
    formulir = models.ForeignKey(Formulir, on_delete=models.PROTECT, related_name="kiriman")
    kontingen = models.ForeignKey(Kontingen, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    peserta = models.ForeignKey(Peserta, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    nama_pengisi = models.CharField(max_length=100, blank=True, help_text="Nama Juri / nama pengisi.")
    akun = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    data = models.JSONField(default=dict)
    dikirim_pada = models.DateTimeField(default=timezone.now)
    terkunci = models.BooleanField(default=True, help_text="Juri tidak bisa mengubah kiriman yang terkunci.")
    client_uuid = models.UUIDField(null=True, blank=True, unique=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    riwayat = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = "kiriman form"
        verbose_name_plural = "kiriman form"
        ordering = ["-dikirim_pada"]
        indexes = [models.Index(fields=["formulir", "kontingen"]), models.Index(fields=["formulir", "peserta"])]

    @property
    def kunci_subjek(self) -> str:
        if self.kontingen_id:
            return f"K{self.kontingen_id}"
        if self.peserta_id:
            return f"P{self.peserta_id}"
        return ""


class PemecahSeri(ModelDasar):
    """Urutan manual superadmin untuk subjek yang nilainya sama (angka kecil = di atas)."""

    formulir = models.ForeignKey(Formulir, on_delete=models.CASCADE, related_name="pemecah_seri")
    kunci_subjek = models.CharField(max_length=20)
    nilai = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["formulir", "kunci_subjek"], name="pemecah_seri_unik")]
