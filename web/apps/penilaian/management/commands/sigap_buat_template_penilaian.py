"""Buat form penilaian DRAF dari data/template_penilaian.json (docs/16-FORM-BUILDER.md).

    python manage.py sigap_buat_template_penilaian
    python manage.py sigap_buat_template_penilaian --file D:\\data\\template_lain.json

Aman diulang: form dengan slug yang sudah ada dilewati (tidak ditimpa). Semua form dibuat berstatus DRAF
dan ditandai "perlu konfirmasi" karena aspek/bobot final dari panitia menyusul (paling lambat 5 November).

Penamaan:
- slug = <kunci>-<tingkat>, misal penilaian-traveling-madya; form tanpa tingkat: <kunci>.
- kunci REF bersama = penilaian-<kegiatan> (form biasa), <kegiatan> (gugur), <kegiatan>-<cabang> (per cabang),
  juara-umum. Sehingga rumus juara umum REF("penilaian-traveling", "peringkat") menemukan form tingkat yang sama.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.absensi.models import Kegiatan
from apps.penilaian import services as svc
from apps.penilaian.models import (
    AksesForm,
    ArahUrut,
    Formulir,
    JenisKolom,
    JenisPenilaian,
    JenisSubjek,
    ModeForm,
    StatusForm,
)

TINGKAT = ["MULA", "MADYA", "WIRA"]


def kunci_template(t: dict) -> str:
    kegiatan = t.get("kegiatan")
    if not kegiatan:
        return slugify(t.get("judul", "form"))
    if t.get("cabang"):
        return f"{kegiatan}-{slugify(t['cabang'])}"
    if t.get("jenis") == "gugur":
        return kegiatan
    return f"penilaian-{kegiatan}"


class Command(BaseCommand):
    help = "Buat form penilaian DRAF dari template pedoman (aman diulang)."

    def add_arguments(self, parser):
        parser.add_argument("--file", default=None, help="Berkas JSON (bawaan: ../data/template_penilaian.json)")

    def handle(self, *args, **o):
        berkas = Path(o["file"]) if o["file"] else Path(settings.BASE_DIR).parent / "data" / "template_penilaian.json"
        try:
            data = json.loads(berkas.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise CommandError(f"Tidak bisa membaca {berkas}: {e}") from None
        dibuat = dilewati = 0
        peringatan: list[str] = []
        for t in data.get("templates", []):
            kunci = kunci_template(t)
            daftar_tingkat = TINGKAT if t.get("per_tingkat", True) else ["SEMUA"]
            for tingkat in daftar_tingkat:
                slug = kunci if tingkat == "SEMUA" else f"{kunci}-{tingkat.lower()}"
                if Formulir.objects.filter(slug=slug).exists():
                    dilewati += 1
                    continue
                self._buat(t, kunci, slug, tingkat, peringatan)
                dibuat += 1
        self.stdout.write(
            self.style.SUCCESS(f"Form penilaian: {dibuat} dibuat (DRAF), {dilewati} sudah ada (dilewati).")
        )
        for p in peringatan:
            self.stdout.write(self.style.WARNING(p))

    @transaction.atomic
    def _buat(self, t: dict, kunci: str, slug: str, tingkat: str, peringatan: list[str]) -> Formulir:
        kegiatan = Kegiatan.objects.filter(kode=t.get("kegiatan") or "").first()
        if t.get("kegiatan") and kegiatan is None:
            peringatan.append(
                f"Kegiatan '{t['kegiatan']}' tidak ada di database (jalankan sigap_seed); {slug} tanpa kegiatan."
            )
        gugur = t.get("jenis") == "gugur"
        tanpa_input = not t.get("kolom_input")
        judul = t["judul"] + ("" if tingkat == "SEMUA" else f" - {tingkat.title()}")
        catatan = "Template dari pedoman, aspek dan bobot belum final (konfirmasi panitia paling lambat 5 November)."
        if t.get("catatan"):
            catatan += " " + t["catatan"]
        f = Formulir.objects.create(
            slug=slug,
            kunci_ref=kunci,
            judul=judul,
            mode=ModeForm.PENILAIAN,
            status=StatusForm.DRAF,
            akses=AksesForm.SUPERADMIN if tanpa_input else AksesForm.JURI,
            jenis_subjek=JenisSubjek.PESERTA if t.get("subjek") == "peserta" else JenisSubjek.KONTINGEN,
            kegiatan=kegiatan,
            tingkat=tingkat,
            cabang=t.get("cabang", ""),
            jenis_penilaian=JenisPenilaian.GUGUR if gugur else JenisPenilaian.BIASA,
            jumlah_juri=3 if "3 juri" in (t.get("catatan") or "") else 1,
            kolom_urut=t.get("urut_berdasarkan", ""),
            arah_urut=ArahUrut.NAIK if t.get("arah_urut") == "naik" else ArahUrut.TURUN,
            perlu_konfirmasi=True,
            catatan=catatan,
        )
        for k in t.get("kolom_input", []):
            data = {
                "jenis": JenisKolom.ANGKA, "kode": k["kode"], "label": k["label"], "wajib": "1",
                "min": k.get("min"), "max": k.get("max"), "desimal": 0 if gugur else 2, "tampil_desimal": 2,
            }  # fmt: skip
            svc.simpan_kolom(None, f, data)
        for k in t.get("kolom_rumus", []):
            data = {
                "jenis": JenisKolom.RUMUS,
                "kode": k["kode"],
                "label": k["label"],
                "rumus": k["rumus"],
                "tampil_desimal": 2,
            }
            try:
                svc.simpan_kolom(None, f, data)
            except svc.GagalForm as e:
                peringatan.append(f"{slug}: rumus [{k['kode']}] belum bisa dibuat: {e.pesan}")
        if f.kolom_urut and not f.kolom.filter(kode=f.kolom_urut).exists():
            f.kolom_urut = ""
            f.save(update_fields=["kolom_urut"])
        return f
