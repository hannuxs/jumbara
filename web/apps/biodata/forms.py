"""Form biodata (publik dan superadmin). Semua aturan divalidasi di server."""

from __future__ import annotations

import secrets
import time
from datetime import date

from django import forms
from django.core import signing
from django.utils import timezone

from apps.absensi import jadwal as jadwal_mod
from apps.absensi.models import Kegiatan
from apps.inti.models import Tingkat
from apps.kontingen.models import Kontingen

from . import foto as foto_mod
from . import nik as nik_mod
from . import services
from .models import PERAN_DEWASA, GolonganDarah, JenisKelamin, Peran

NAMA_BULAN = [
    (1, "Januari"), (2, "Februari"), (3, "Maret"), (4, "April"), (5, "Mei"), (6, "Juni"),
    (7, "Juli"), (8, "Agustus"), (9, "September"), (10, "Oktober"), (11, "November"), (12, "Desember"),
]  # fmt: skip

PENJELASAN_PERAN = {
    Peran.PESERTA: "Anggota PMR yang ikut lomba/kegiatan",
    Peran.PIMPINAN_KONTINGEN: "Guru/pembina yang memimpin kontingen",
    Peran.PEMBINA_PENDAMPING: "Guru/pembina yang mendampingi",
    Peran.PENINJAU: "Pembina atau anggota PMR yang ikut mengamati",
}

SALT_TOKEN = "sigap.biodata.token"


class PilihanKontingen(forms.ModelChoiceField):
    def label_from_instance(self, obj: Kontingen) -> str:
        return obj.nama


class TanggalTigaPilihan(forms.MultiWidget):
    """Tanggal lahir sebagai tiga pilihan (hari, bulan, tahun) agar ramah HP."""

    def __init__(self, attrs=None):
        tahun_ini = timezone.localdate().year
        hari = [("", "Tgl")] + [(i, str(i)) for i in range(1, 32)]
        bulan = [("", "Bulan")] + NAMA_BULAN
        tahun = [("", "Tahun")] + [(t, str(t)) for t in range(tahun_ini - 3, tahun_ini - 91, -1)]
        super().__init__(
            [
                forms.Select(attrs={"aria-label": "Tanggal lahir", "class": "input"}, choices=hari),
                forms.Select(attrs={"aria-label": "Bulan lahir", "class": "input"}, choices=bulan),
                forms.Select(attrs={"aria-label": "Tahun lahir", "class": "input"}, choices=tahun),
            ],
            attrs,
        )

    def decompress(self, value):
        if isinstance(value, date):
            return [value.day, value.month, value.year]
        return [None, None, None]


class TanggalLahirField(forms.MultiValueField):
    widget = TanggalTigaPilihan

    def __init__(self, **kwargs):
        fields = (forms.IntegerField(), forms.IntegerField(), forms.IntegerField())
        super().__init__(
            fields=fields,
            require_all_fields=True,
            error_messages={
                "required": "Tanggal lahir wajib diisi.",
                "incomplete": "Pilih tanggal, bulan, dan tahun lahir.",
            },
            **kwargs,
        )

    def compress(self, data_list):
        if not data_list or None in data_list:
            return None
        hari, bulan, tahun = data_list
        try:
            return date(int(tahun), int(bulan), int(hari))
        except ValueError:
            raise forms.ValidationError("Tanggal lahir tidak ada di kalender. Periksa lagi.") from None


class BiodataForm(forms.Form):
    """Form biodata. `mode="publik"` untuk form tanpa login, `"superadmin"` untuk tambah/ubah."""

    kontingen = PilihanKontingen(
        queryset=Kontingen.objects.none(),
        label="Utusan sekolah",
        empty_label="Pilih sekolah",
        error_messages={"required": "Pilih utusan sekolah.", "invalid_choice": "Pilih sekolah dari daftar."},
    )
    tingkat = forms.ChoiceField(
        choices=Tingkat.choices,
        widget=forms.RadioSelect,
        label="Tingkat",
        error_messages={"required": "Pilih tingkat."},
    )
    peran = forms.ChoiceField(
        choices=Peran.choices,
        widget=forms.RadioSelect,
        label="Peran",
        error_messages={"required": "Pilih peran Anda."},
    )
    kegiatan = forms.ModelMultipleChoiceField(
        queryset=Kegiatan.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Kegiatan yang diikuti",
        help_text="Boleh lebih dari satu, asal jadwalnya tidak bertabrakan. Boleh dikosongkan.",
        error_messages={"invalid_choice": "Pilihan kegiatan tidak dikenal. Muat ulang halaman."},
    )
    nama_lengkap = forms.CharField(
        label="Nama lengkap",
        max_length=200,
        error_messages={"required": "Nama lengkap wajib diisi."},
        widget=forms.TextInput(attrs={"autocomplete": "name", "autocapitalize": "words"}),
    )
    nik = forms.CharField(
        label="NIK",
        max_length=30,
        help_text="NIK ada di Kartu Keluarga (KK). 16 angka.",
        error_messages={"required": "NIK wajib diisi."},
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off", "maxlength": "16"}),
    )
    nomor_induk_anggota = forms.CharField(
        label="Nomor Induk Anggota PMR (jika ada)",
        max_length=50,
        required=False,
        help_text="Terdapat pada aplikasi SIAMO.",
    )
    jenis_kelamin = forms.ChoiceField(
        choices=JenisKelamin.choices,
        widget=forms.RadioSelect,
        label="Jenis kelamin",
        error_messages={"required": "Pilih jenis kelamin."},
    )
    tempat_lahir = forms.CharField(
        label="Tempat lahir",
        max_length=100,
        error_messages={"required": "Tempat lahir wajib diisi."},
    )
    tanggal_lahir = TanggalLahirField(label="Tanggal lahir")
    alamat = forms.CharField(
        label="Alamat rumah",
        max_length=400,
        widget=forms.Textarea(attrs={"rows": 3, "autocomplete": "street-address"}),
        error_messages={"required": "Alamat rumah wajib diisi."},
    )
    golongan_darah = forms.ChoiceField(
        choices=GolonganDarah.choices,
        widget=forms.RadioSelect,
        label="Golongan darah",
        error_messages={"required": "Pilih golongan darah (pilih “Belum tahu” jika tidak tahu)."},
    )
    telepon = forms.CharField(
        label="Nomor HP/WhatsApp",
        max_length=25,
        required=False,
        widget=forms.TextInput(attrs={"inputmode": "tel", "autocomplete": "tel"}),
    )
    nama_orang_tua = forms.CharField(label="Nama ayah atau ibu (atau wali)", max_length=200, required=False)
    telepon_orang_tua = forms.CharField(
        label="Nomor HP ayah atau ibu (atau wali)",
        max_length=25,
        required=False,
        help_text="Untuk kontak darurat.",
        widget=forms.TextInput(attrs={"inputmode": "tel"}),
    )
    foto = forms.FileField(
        label="Foto",
        required=False,
        widget=forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png"}),
    )
    foto_potong = forms.CharField(required=False, widget=forms.HiddenInput)
    persetujuan = forms.BooleanField(
        required=False,
        label=(
            "Saya menyatakan data ini benar. Saya (atau orang tua/wali saya) menyetujui data ini "
            "dipakai panitia Jumbara PMR Kabupaten Bulungan V 2026 untuk keperluan acara, termasuk "
            "kartu peserta, absensi, dan piagam."
        ),
    )
    # Anti-bot (hanya mode publik).
    situs_web = forms.CharField(required=False, label="Jangan diisi")
    token = forms.CharField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, mode: str = "publik", peserta=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = mode
        self.peserta = peserta
        self.hasil_foto: foto_mod.HasilFoto | None = None
        self.nik_dobel = False
        self.fields["kontingen"].queryset = Kontingen.objects.order_by("tingkat", "nama")
        self.fields["kegiatan"].queryset = Kegiatan.objects.filter(bisa_dipilih=True).order_by("urutan", "nama")
        if mode != "publik":
            for nama in ("situs_web", "token", "persetujuan"):
                del self.fields[nama]
        for field in self.fields.values():
            w = field.widget
            if isinstance(w, forms.TextInput | forms.Textarea | forms.Select) and not isinstance(w, forms.RadioSelect):
                w.attrs.setdefault("class", "input")

    def data_kegiatan(self) -> dict[str, list[dict]]:
        """Jadwal dan bentrok kegiatan per tingkat untuk JavaScript form (json_script)."""
        return jadwal_mod.semua_tingkat()

    def kegiatan_terpilih(self) -> list[int]:
        """Id kegiatan yang tercentang (dari kiriman atau data awal) untuk menandai kotak centang."""
        if self.is_bound:
            return [int(v) for v in self.data.getlist("kegiatan") if str(v).isdigit()]
        return [getattr(k, "pk", k) for k in self.initial.get("kegiatan", [])]

    def pilihan_kontingen_berkelompok(self) -> list[tuple[str, list[Kontingen]]]:
        urutan = [Tingkat.MULA, Tingkat.MADYA, Tingkat.WIRA]
        semua = list(self.fields["kontingen"].queryset)
        return [(t.label, [k for k in semua if k.tingkat == t.value]) for t in urutan]

    # --- Validasi per isian ---------------------------------------------------

    def clean_nama_lengkap(self) -> str:
        nama = services.rapikan_spasi(self.cleaned_data["nama_lengkap"]).replace("’", "'")
        if len(nama) < 3:
            raise forms.ValidationError("Nama terlalu pendek (minimal 3 huruf).")
        if len(nama) > 100:
            raise forms.ValidationError("Nama terlalu panjang (maksimal 100 karakter).")
        if not services.nama_valid(nama):
            raise forms.ValidationError(
                "Nama hanya boleh berisi huruf, spasi, titik, koma, apostrof ('), dan tanda hubung (-)."
            )
        # Semua nama disimpan HURUF KAPITAL, termasuk gelar (REVISI R3).
        return services.kapital(nama)

    def clean_nik(self) -> str:
        nik = "".join(self.cleaned_data["nik"].split())
        if not nik.isdigit():
            raise forms.ValidationError("NIK hanya boleh berisi angka.")
        if len(nik) != 16:
            raise forms.ValidationError(f"NIK harus tepat 16 angka (sekarang {len(nik)} angka).")
        if not nik_mod.format_valid(nik):
            raise forms.ValidationError("NIK tidak valid. Periksa lagi di Kartu Keluarga.")
        kecuali = self.peserta.pk if self.peserta else None
        if services.nik_terdaftar(nik, kecuali_pk=kecuali):
            self.nik_dobel = True
            raise forms.ValidationError(
                "NIK ini sudah terdaftar. Jika Anda merasa belum pernah mengisi atau ingin memperbaiki "
                "data, hubungi superadmin."
            )
        return nik

    def clean_nomor_induk_anggota(self) -> str:
        return services.rapikan_spasi(self.cleaned_data.get("nomor_induk_anggota", ""))

    def clean_tempat_lahir(self) -> str:
        teks = services.rapikan_spasi(self.cleaned_data["tempat_lahir"])
        if not 2 <= len(teks) <= 60:
            raise forms.ValidationError("Tempat lahir 2 sampai 60 huruf.")
        if any(c.isdigit() for c in teks):
            raise forms.ValidationError("Tempat lahir tidak boleh berisi angka.")
        return teks

    def clean_tanggal_lahir(self) -> date:
        tgl = self.cleaned_data["tanggal_lahir"]
        if tgl > timezone.localdate():
            raise forms.ValidationError("Tanggal lahir tidak boleh di masa depan.")
        if tgl.year < 1930:
            raise forms.ValidationError("Tahun lahir tidak wajar. Periksa lagi.")
        return tgl

    def clean_alamat(self) -> str:
        teks = " ".join(self.cleaned_data["alamat"].split())
        if len(teks) < 10:
            raise forms.ValidationError("Alamat terlalu pendek (minimal 10 karakter). Tulis jalan, RT, desa/kelurahan.")
        if len(teks) > 300:
            raise forms.ValidationError("Alamat terlalu panjang (maksimal 300 karakter).")
        return teks

    def _telepon(self, nama: str) -> str:
        teks = self.cleaned_data.get(nama, "").strip()
        if not teks:
            return ""
        nomor = services.normalisasi_telepon(teks)
        if nomor is None:
            raise forms.ValidationError("Nomor HP tidak valid. Contoh: 081234567890.")
        return nomor

    def clean_telepon(self) -> str:
        return self._telepon("telepon")

    def clean_telepon_orang_tua(self) -> str:
        return self._telepon("telepon_orang_tua")

    def clean_nama_orang_tua(self) -> str:
        nama = services.rapikan_spasi(self.cleaned_data.get("nama_orang_tua", "")).replace("’", "'")
        if nama and (len(nama) < 3 or not services.nama_valid(nama)):
            raise forms.ValidationError("Nama orang tua/wali hanya huruf, minimal 3 huruf.")
        return services.kapital(nama[:100])

    # --- Validasi gabungan ----------------------------------------------------

    def clean(self):
        data = super().clean()
        kontingen, tingkat = data.get("kontingen"), data.get("tingkat")
        if self.mode == "publik" and kontingen and tingkat and kontingen.tingkat != tingkat:
            # REVISI R1: tingkat dipilih dulu, sekolah harus sesuai tingkat. Superadmin tetap boleh
            # (misalnya memindahkan orang), dan akan mendapat tanda TINGKAT_BEDA.
            self.add_error(
                "kontingen",
                f"{kontingen.nama} bukan sekolah tingkat {Tingkat(tingkat).label}. Pilih lagi tingkat atau sekolah.",
            )
        peran = data.get("peran")
        if peran:
            dewasa = peran in PERAN_DEWASA
            if dewasa and not data.get("telepon") and "telepon" not in self.errors:
                self.add_error("telepon", "Nomor HP wajib diisi untuk Pimpinan Kontingen dan Pembina Pendamping.")
            if not dewasa:
                if not data.get("nama_orang_tua") and "nama_orang_tua" not in self.errors:
                    self.add_error("nama_orang_tua", "Nama ayah/ibu/wali wajib diisi.")
                if not data.get("telepon_orang_tua") and "telepon_orang_tua" not in self.errors:
                    self.add_error("telepon_orang_tua", "Nomor HP ayah/ibu/wali wajib diisi.")

        kegiatan = list(data.get("kegiatan") or [])
        if kegiatan and tingkat:
            for pesan in jadwal_mod.periksa(tingkat, kegiatan):
                self.add_error("kegiatan", pesan)

        berkas = data.get("foto")
        if berkas:
            try:
                self.hasil_foto = foto_mod.proses(berkas, foto_mod.baca_potongan(data.get("foto_potong", "")))
            except foto_mod.FotoTidakValid as e:
                self.add_error("foto", str(e))
        elif not (self.peserta and self.peserta.foto_path):
            # Foto wajib mutlak karena dicetak di kartu (REVISI R2).
            self.add_error("foto", "Foto wajib diunggah.")

        if self.mode == "publik":
            if not data.get("persetujuan"):
                self.add_error("persetujuan", "Centang pernyataan ini untuk melanjutkan.")
            if data.get("situs_web"):
                raise forms.ValidationError("Kiriman tidak dapat diproses. Muat ulang halaman lalu coba lagi.")
        return data


# --- Token kiriman sekali pakai (juga pengukur waktu pengisian) ------------------


def buat_token() -> str:
    return signing.dumps({"n": secrets.token_hex(16), "t": time.time()}, salt=SALT_TOKEN)


def baca_token(token: str, umur_maks: int = 24 * 3600) -> tuple[str, float] | None:
    """(nonce, detik sejak halaman dibuka) atau None bila token rusak/kedaluwarsa."""
    if not token:
        return None
    try:
        data = signing.loads(token, salt=SALT_TOKEN, max_age=umur_maks)
        return str(data["n"]), time.time() - float(data["t"])
    except (signing.BadSignature, KeyError, TypeError, ValueError):
        return None
