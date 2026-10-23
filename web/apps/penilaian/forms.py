"""Django Form dinamis untuk mengisi form builder (validasi selalu di server)."""

from __future__ import annotations

import re
from pathlib import Path

from django import forms

from .models import JenisKolom, Kolom

EKSTENSI_BAWAAN = ["pdf", "jpg", "jpeg", "png"]
UKURAN_BAWAAN_MB = 5
EKSTENSI_DILARANG = {
    "exe",
    "bat",
    "cmd",
    "com",
    "js",
    "vbs",
    "ps1",
    "msi",
    "dll",
    "scr",
    "html",
    "htm",
    "svg",
    "php",
    "py",
}
TANDA_TANGAN = {
    "pdf": [b"%PDF"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "png": [b"\x89PNG"],
    "docx": [b"PK\x03\x04"],
    "xlsx": [b"PK\x03\x04"],
    "pptx": [b"PK\x03\x04"],
    "zip": [b"PK\x03\x04"],
    "mp4": [b"ftyp"],
}


def _angka(teks) -> float | None:
    if teks in (None, ""):
        return None
    try:
        return float(str(teks).replace(",", "."))
    except ValueError:
        return None


class IsianAngka(forms.CharField):
    """Angka yang menerima koma desimal; batas min/max/desimal dari pengaturan kolom."""

    def __init__(self, *a, minimal=None, maksimal=None, desimal=0, **kw):
        self.minimal, self.maksimal, self.desimal = minimal, maksimal, desimal
        super().__init__(*a, **kw)

    def clean(self, value):
        value = super().clean(value)
        if value in ("", None):
            return None
        teks = str(value).strip().replace(",", ".")
        if not re.fullmatch(r"-?\d+(\.\d+)?", teks):
            raise forms.ValidationError("Isi dengan angka, misalnya 85 atau 85,5.")
        angka = float(teks)
        if self.desimal == 0 and angka != int(angka):
            raise forms.ValidationError("Isi dengan angka bulat (tanpa koma).")
        if self.desimal and len(teks.split(".")[1] if "." in teks else "") > self.desimal:
            raise forms.ValidationError(f"Paling banyak {self.desimal} angka di belakang koma.")
        if self.minimal is not None and angka < self.minimal:
            raise forms.ValidationError(f"Paling kecil {self.minimal:g}.")
        if self.maksimal is not None and angka > self.maksimal:
            raise forms.ValidationError(f"Paling besar {self.maksimal:g}.")
        return int(angka) if self.desimal == 0 else angka


class IsianBerkas(forms.FileField):
    def __init__(self, *a, ekstensi=None, ukuran_mb=None, **kw):
        self.ekstensi = [
            e.lower().lstrip(".")
            for e in (ekstensi or EKSTENSI_BAWAAN)
            if e.lower().lstrip(".") not in EKSTENSI_DILARANG
        ]
        self.ukuran_mb = min(float(ukuran_mb or UKURAN_BAWAAN_MB), 20)
        super().__init__(*a, **kw)

    def clean(self, data, initial=None):
        berkas = super().clean(data, initial)
        if not berkas:
            return berkas
        ext = Path(berkas.name).suffix.lower().lstrip(".")
        if ext not in self.ekstensi:
            raise forms.ValidationError(f"Jenis file harus: {', '.join(self.ekstensi)}.")
        if berkas.size > self.ukuran_mb * 1024 * 1024:
            raise forms.ValidationError(f"Ukuran file paling besar {self.ukuran_mb:g} MB.")
        awal = berkas.read(16)
        berkas.seek(0)
        tanda = TANDA_TANGAN.get(ext)
        if tanda and not any(t in awal for t in tanda):
            raise forms.ValidationError("Isi file tidak sesuai dengan jenisnya.")
        return berkas


def field_kolom(k: Kolom) -> forms.Field | None:
    """Satu field Django untuk satu kolom isian (None untuk judul/kolom hitung)."""
    umum = {"label": k.label, "required": k.wajib, "help_text": k.bantuan}
    j = k.jenis
    if j == JenisKolom.TEKS:
        return forms.CharField(max_length=int(k.atur("maks", 300) or 300), **umum)
    if j == JenisKolom.PARAGRAF:
        return forms.CharField(
            max_length=int(k.atur("maks", 3000) or 3000), widget=forms.Textarea(attrs={"rows": 4}), **umum
        )
    if j == JenisKolom.ANGKA:
        return IsianAngka(
            minimal=_angka(k.atur("min")), maksimal=_angka(k.atur("max")), desimal=int(k.atur("desimal", 0) or 0),
            widget=forms.TextInput(attrs={"inputmode": "decimal", "autocomplete": "off"}), **umum,
        )  # fmt: skip
    if j == JenisKolom.SKALA:
        return forms.TypedChoiceField(
            choices=[(str(i), str(i)) for i in range(1, 6)],
            coerce=int,
            empty_value=None,
            widget=forms.RadioSelect,
            **umum,
        )
    if j in (JenisKolom.PILIHAN, JenisKolom.DROPDOWN):
        pilihan = [(p, p) for p in k.atur("pilihan", [])]
        if j == JenisKolom.DROPDOWN:
            return forms.ChoiceField(choices=[("", "Pilih...")] + pilihan, **umum)
        return forms.ChoiceField(choices=pilihan, widget=forms.RadioSelect, **umum)
    if j == JenisKolom.CENTANG:
        return forms.MultipleChoiceField(
            choices=[(p, p) for p in k.atur("pilihan", [])], widget=forms.CheckboxSelectMultiple, **umum
        )
    if j == JenisKolom.TANGGAL:
        return forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), **umum)
    if j == JenisKolom.JAM:
        return forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}), **umum)
    if j == JenisKolom.YA_TIDAK:
        return forms.TypedChoiceField(
            choices=[("ya", "Ya"), ("tidak", "Tidak")], widget=forms.RadioSelect, empty_value=None, **umum
        )
    if j == JenisKolom.BERKAS:
        return IsianBerkas(ekstensi=k.atur("tipe_berkas"), ukuran_mb=k.atur("ukuran_mb"), **umum)
    return None


class FormIsian(forms.Form):
    """Isian satu kiriman. `nama_pengisi` wajib (Nama Juri untuk mode 2)."""

    def __init__(
        self, kolom: list[Kolom], *a, label_nama: str = "Nama Juri", minta_nama: bool = True, awal_data=None, **kw
    ):
        super().__init__(*a, **kw)
        self.kolom = [k for k in kolom if k.diisi]
        self.kolom_tampil = kolom
        if minta_nama:
            self.fields["nama_pengisi"] = forms.CharField(label=label_nama, max_length=60, required=True)
        for k in self.kolom:
            f = field_kolom(k)
            if f is not None:
                self.fields[f"k_{k.kode}"] = f
                if awal_data and k.kode in awal_data and k.jenis != JenisKolom.BERKAS:
                    self.initial[f"k_{k.kode}"] = awal_data[k.kode]

    def clean_nama_pengisi(self) -> str:
        nama = " ".join(self.cleaned_data["nama_pengisi"].split())
        if len(nama) < 2:
            raise forms.ValidationError("Isi nama dengan benar.")
        return nama

    def data_bersih(self) -> tuple[dict, dict]:
        """(isian JSON tanpa file, {kode: UploadedFile})."""
        data, berkas = {}, {}
        for k in self.kolom:
            v = self.cleaned_data.get(f"k_{k.kode}")
            if k.jenis == JenisKolom.BERKAS:
                if v:
                    berkas[k.kode] = v
                continue
            if v is None or v == "" or v == []:
                data[k.kode] = None
            elif k.jenis == JenisKolom.TANGGAL:
                data[k.kode] = v.isoformat()
            elif k.jenis == JenisKolom.JAM:
                data[k.kode] = v.strftime("%H:%M")
            else:
                data[k.kode] = v
        return data, berkas

    def baris(self):
        """Urutan tampil: (kolom, field terikat atau None untuk judul bagian)."""
        for k in self.kolom_tampil:
            if k.jenis == JenisKolom.JUDUL:
                yield k, None
            elif k.diisi:
                yield k, self[f"k_{k.kode}"]
