"""Form pengaturan form builder (superadmin)."""

from __future__ import annotations

from django import forms
from django.utils.text import slugify

from apps.kontingen.models import Kontingen

from .models import AksesForm, Formulir, JenisSubjek, ModeForm


class FormPengaturan(forms.ModelForm):
    class Meta:
        model = Formulir
        fields = [
            "judul", "deskripsi", "mode", "status", "akses", "buka_pada", "tutup_pada", "jenis_subjek",
            "satu_per_subjek", "kegiatan", "tingkat", "cabang", "jenis_penilaian", "agregasi", "jumlah_juri",
            "subjek_kontingen", "kolom_urut", "arah_urut", "juri_lihat_hasil", "slug", "kunci_ref", "catatan",
        ]  # fmt: skip
        labels = {
            "judul": "Judul form",
            "deskripsi": "Deskripsi (tampil di atas form)",
            "buka_pada": "Buka mulai (kosong = langsung)",
            "tutup_pada": "Tutup pada (kosong = tanpa batas)",
            "jenis_subjek": "Subjek",
            "satu_per_subjek": "Satu kiriman per subjek (mode 1)",
            "kegiatan": "Kegiatan (untuk poin kehadiran)",
            "cabang": "Cabang (opsional, misal Bakiak)",
            "jenis_penilaian": "Jenis penilaian",
            "agregasi": "Nilai dari beberapa juri",
            "jumlah_juri": "Target jumlah juri per subjek",
            "subjek_kontingen": "Hanya kontingen tertentu (kosong = semua kontingen tingkat ini)",
            "kolom_urut": "Peringkat berdasarkan kolom",
            "arah_urut": "Arah peringkat",
            "juri_lihat_hasil": "Juri boleh melihat tabel hasil",
            "slug": "Slug (alamat dan nama untuk REF)",
            "kunci_ref": "Kunci REF bersama antartingkat (opsional, misal penilaian-traveling)",
            "catatan": "Catatan superadmin",
        }
        widgets = {
            "deskripsi": forms.Textarea(attrs={"rows": 3}),
            "catatan": forms.Textarea(attrs={"rows": 2}),
            "buka_pada": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "tutup_pada": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "subjek_kontingen": forms.CheckboxSelectMultiple,
            "kolom_urut": forms.Select,
        }

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["subjek_kontingen"].queryset = Kontingen.objects.order_by("kode")
        self.fields["slug"].required = False
        f = self.instance
        pilihan = [("", "(tanpa peringkat)")]
        if f.pk:
            from .hasil import nama_tersedia

            pilihan += [(k, f"[{k}] {v}") for k, v in nama_tersedia(f).items()]
        self.fields["kolom_urut"].widget = forms.Select(choices=pilihan)
        self.fields["kolom_urut"].required = False
        for nama in ("buka_pada", "tutup_pada"):
            self.fields[nama].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"]
        for fld in self.fields.values():
            if not isinstance(fld.widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.RadioSelect)):
                fld.widget.attrs.setdefault("class", "input")

    def clean_slug(self) -> str:
        slug = slugify(self.cleaned_data.get("slug") or self.cleaned_data.get("judul") or "")[:80]
        if not slug:
            raise forms.ValidationError("Slug wajib diisi.")
        if Formulir.objects.filter(slug=slug).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Slug sudah dipakai form lain.")
        return slug

    def clean_kunci_ref(self) -> str:
        return slugify(self.cleaned_data.get("kunci_ref") or "")[:80]

    def clean(self):
        data = super().clean()
        mode, subjek, akses = data.get("mode"), data.get("jenis_subjek"), data.get("akses")
        if mode == ModeForm.PENILAIAN and subjek == JenisSubjek.BEBAS:
            self.add_error("jenis_subjek", "Form penilaian harus per kontingen atau per orang.")
        if akses == AksesForm.PUBLIK and subjek == JenisSubjek.PESERTA:
            # Daftar nama peserta tidak boleh tampil di halaman publik (UU PDP).
            self.add_error("akses", "Form publik tidak bisa memakai subjek per orang (daftar nama tidak boleh publik).")
        if akses == AksesForm.PUBLIK and mode == ModeForm.PENILAIAN:
            self.add_error("akses", "Form penilaian hanya untuk juri atau superadmin.")
        buka, tutup = data.get("buka_pada"), data.get("tutup_pada")
        if buka and tutup and tutup <= buka:
            self.add_error("tutup_pada", "Waktu tutup harus setelah waktu buka.")
        if not data.get("jumlah_juri"):
            data["jumlah_juri"] = 1
        return data
