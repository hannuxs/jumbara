"""Logika form builder: kolom, kiriman, kunci, salin, berkas privat."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.inti.log import catat
from apps.inti.utils import ip_klien, user_agent

from . import rumus as r
from .hasil import BAWAAN, Subjek, validasi_rumus
from .models import (
    AksesForm,
    Formulir,
    JenisKolom,
    JenisSubjek,
    Kiriman,
    Kolom,
    ModeForm,
    PemecahSeri,
    StatusForm,
)

POLA_KODE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
DICADANGKAN = set(BAWAAN) | {"nama_pengisi", "subjek", "pemecah_seri"}


class GagalForm(Exception):
    def __init__(self, pesan: str):
        super().__init__(pesan)
        self.pesan = pesan


def nama_pelaku(request) -> str:
    return getattr(request, "nama_pelaku", "") or getattr(getattr(request, "user", None), "username", "") or ""


# --- Kode dan slug ----------------------------------------------------------------------------------------


def kode_dari_label(label: str, terpakai: set[str]) -> str:
    dasar = re.sub(r"[^a-z0-9_]", "", slugify(label).replace("-", "_"))[:30] or "kolom"
    if not dasar[0].isalpha():
        dasar = "k_" + dasar
    kode, i = dasar, 2
    while kode in terpakai or kode in DICADANGKAN:
        kode = f"{dasar}_{i}"
        i += 1
    return kode


def slug_unik(teks: str, kecuali_pk: int | None = None) -> str:
    dasar = slugify(teks)[:70] or "form"
    slug, i = dasar, 2
    while Formulir.objects.filter(slug=slug).exclude(pk=kecuali_pk).exists():
        slug = f"{dasar}-{i}"
        i += 1
    return slug


# --- Kolom ------------------------------------------------------------------------------------------------


def bersihkan_pengaturan(f: Formulir, jenis: str, kode: str, data: dict) -> dict:
    """Validasi pengaturan kolom sesuai jenis; GagalForm bila salah."""
    p: dict = {}

    def angka(kunci):
        v = data.get(kunci)
        if v in (None, ""):
            return None
        try:
            return float(str(v).replace(",", "."))
        except ValueError:
            raise GagalForm(f"Isian {kunci} harus angka.") from None

    if jenis == JenisKolom.ANGKA:
        p["min"], p["max"] = angka("min"), angka("max")
        if p["min"] is not None and p["max"] is not None and p["min"] > p["max"]:
            raise GagalForm("Nilai minimal lebih besar dari maksimal.")
        p["desimal"] = int(angka("desimal") or 0)
        if not 0 <= p["desimal"] <= 4:
            raise GagalForm("Desimal 0 sampai 4.")
    if jenis in (JenisKolom.PILIHAN, JenisKolom.DROPDOWN, JenisKolom.CENTANG):
        pilihan = data.get("pilihan") or []
        if isinstance(pilihan, str):
            pilihan = pilihan.splitlines()
        pilihan = list(dict.fromkeys(" ".join(x.split()) for x in pilihan if x and x.strip()))
        if len(pilihan) < 2:
            raise GagalForm("Isi minimal 2 pilihan (satu per baris).")
        p["pilihan"] = [x[:150] for x in pilihan[:100]]
    if jenis == JenisKolom.BERKAS:
        teks = data.get("tipe_berkas") or "pdf, jpg, jpeg, png"
        p["tipe_berkas"] = [x.strip().lower().lstrip(".") for x in re.split(r"[,\s]+", teks) if x.strip()]
        p["ukuran_mb"] = min(angka("ukuran_mb") or 5, 20)
    if jenis == JenisKolom.OTOMATIS:
        sumber = data.get("sumber") or "poin_kehadiran"
        if sumber not in BAWAAN:
            raise GagalForm("Sumber kolom otomatis tidak dikenal.")
        p["sumber"] = sumber
    if jenis == JenisKolom.RUMUS:
        teks = (data.get("rumus") or "").strip()
        try:
            validasi_rumus(f, kode, teks)
        except r.GalatRumus as e:
            raise GagalForm(f"Rumus belum benar: {e}") from None
        p["rumus"] = teks
    if jenis == JenisKolom.PERINGKAT:
        dasar = (data.get("dasar") or "").strip().lower()
        if not f.kolom.filter(kode=dasar).exists() and dasar not in BAWAAN:
            raise GagalForm("Pilih kolom dasar peringkat yang ada di form ini.")
        if dasar == kode:
            raise GagalForm("Kolom peringkat tidak bisa berdasarkan dirinya sendiri.")
        p["dasar"] = dasar
        p["arah"] = "NAIK" if data.get("arah") == "NAIK" else "TURUN"
    if jenis in (JenisKolom.RUMUS, JenisKolom.OTOMATIS, JenisKolom.ANGKA, JenisKolom.PERINGKAT):
        p["tampil_desimal"] = int(angka("tampil_desimal") if angka("tampil_desimal") is not None else 2)
    if jenis in (JenisKolom.TEKS, JenisKolom.PARAGRAF) and data.get("maks"):
        p["maks"] = int(angka("maks"))
    return p


@transaction.atomic
def simpan_kolom(request, f: Formulir, data: dict, kolom: Kolom | None = None) -> Kolom:
    jenis = data.get("jenis") or (kolom.jenis if kolom else "")
    if jenis not in JenisKolom.values:
        raise GagalForm("Jenis kolom tidak dikenal.")
    label = " ".join((data.get("label") or "").split())[:200]
    if not label:
        raise GagalForm("Label kolom wajib diisi.")
    terpakai = set(f.kolom.exclude(pk=getattr(kolom, "pk", None)).values_list("kode", flat=True))
    kode = (data.get("kode") or "").strip().lower() or (kolom.kode if kolom else kode_dari_label(label, terpakai))
    if not POLA_KODE.match(kode):
        raise GagalForm("Kode kolom: huruf kecil, angka, garis bawah; diawali huruf (contoh nilai_akhir).")
    if kode in terpakai:
        raise GagalForm(f"Kode [{kode}] sudah dipakai kolom lain.")
    if kode in DICADANGKAN and not (jenis == JenisKolom.OTOMATIS and data.get("sumber") == kode):
        raise GagalForm(f"Kode [{kode}] dicadangkan sistem. Pakai nama lain.")
    if f.mode == ModeForm.INPUT and jenis in (JenisKolom.OTOMATIS, JenisKolom.RUMUS, JenisKolom.PERINGKAT):
        raise GagalForm("Kolom otomatis, rumus, dan peringkat hanya untuk form penilaian (mode 2).")
    if kolom and kolom.kode != kode and _kode_dipakai_rumus(f, kolom.kode):
        raise GagalForm(f"Kode [{kolom.kode}] dipakai di rumus lain; ubah rumus itu dulu.")
    pengaturan = bersihkan_pengaturan(f, jenis, kode, data)
    lama = None
    if kolom is None:
        urutan = (f.kolom.order_by("-urutan").values_list("urutan", flat=True).first() or 0) + 10
        kolom = Kolom(formulir=f, urutan=urutan)
    else:
        lama = {"kode": kolom.kode, "label": kolom.label, "jenis": kolom.jenis, "pengaturan": kolom.pengaturan}
    kolom.kode, kolom.label, kolom.jenis, kolom.pengaturan = kode, label, jenis, pengaturan
    kolom.bantuan = " ".join((data.get("bantuan") or "").split())[:300]
    kolom.wajib = bool(data.get("wajib")) and kolom.diisi
    kolom.save()
    catat(request, "form.kolom_diubah" if lama else "form.kolom_ditambah", f, keterangan=f"[{kode}] {label}", lama=lama,
          baru={"kode": kode, "label": label, "jenis": jenis, "pengaturan": pengaturan})  # fmt: skip
    return kolom


def _kode_dipakai_rumus(f: Formulir, kode: str) -> bool:
    for k in f.kolom.filter(jenis__in=[JenisKolom.RUMUS, JenisKolom.PERINGKAT]):
        if k.jenis == JenisKolom.PERINGKAT and k.atur("dasar") == kode:
            return True
        try:
            if kode in r.rujukan(r.urai(k.atur("rumus", ""))).kolom:
                return True
        except r.GalatRumus:
            continue
    return f.kolom_urut == kode


@transaction.atomic
def hapus_kolom(request, kolom: Kolom) -> None:
    f = kolom.formulir
    if _kode_dipakai_rumus(f, kolom.kode):
        raise GagalForm(f"Kolom [{kolom.kode}] dipakai di rumus/peringkat/urutan; ubah itu dulu.")
    if f.kiriman.exists() and kolom.diisi:
        raise GagalForm(
            "Form sudah punya kiriman; kolom isian tidak bisa dihapus (data lama akan hilang). Arsipkan form atau salin."
        )
    catat(request, "form.kolom_dihapus", f, keterangan=f"[{kolom.kode}] {kolom.label}")
    kolom.delete()


@transaction.atomic
def urutkan_kolom(request, f: Formulir, daftar_id: list[int]) -> None:
    milik = {k.pk: k for k in f.kolom.all()}
    if set(daftar_id) != set(milik):
        raise GagalForm("Daftar kolom tidak lengkap. Muat ulang halaman.")
    for i, pk in enumerate(daftar_id, start=1):
        Kolom.objects.filter(pk=pk).update(urutan=i * 10)
    catat(request, "form.kolom_diurutkan", f)


# --- Form ---------------------------------------------------------------------------------------------------


@transaction.atomic
def salin_form(request, f: Formulir, judul: str | None = None, tingkat: str | None = None) -> Formulir:
    baru = Formulir.objects.get(pk=f.pk)
    baru.pk = None
    baru.id = None
    baru.judul = judul or f"{f.judul} (salinan)"
    baru.tingkat = tingkat or f.tingkat
    baru.slug = slug_unik(baru.judul)
    baru.status = StatusForm.DRAF
    baru.terkunci = False
    baru.terkunci_pada = None
    baru.terkunci_oleh = ""
    baru.dibuat_pada = timezone.now()
    baru.save()
    if not tingkat or tingkat == f.tingkat:
        baru.subjek_kontingen.set(f.subjek_kontingen.all())
        baru.subjek_peserta.set(f.subjek_peserta.all())
    for k in f.kolom.all():
        Kolom.objects.create(formulir=baru, kode=k.kode, label=k.label, bantuan=k.bantuan, jenis=k.jenis, wajib=k.wajib,
                             urutan=k.urutan, pengaturan=k.pengaturan)  # fmt: skip
    catat(request, "form.disalin", baru, keterangan=f"Dari {f.slug}")
    return baru


@transaction.atomic
def atur_kunci_form(request, f: Formulir, kunci: bool) -> None:
    f.terkunci = kunci
    f.terkunci_pada = timezone.now() if kunci else None
    f.terkunci_oleh = nama_pelaku(request) if kunci else ""
    f.save(update_fields=["terkunci", "terkunci_pada", "terkunci_oleh", "diubah_pada"])
    catat(request, "form.dikunci" if kunci else "form.dibuka_kuncinya", f)


@transaction.atomic
def atur_kunci_kiriman(request, x: Kiriman, kunci: bool) -> None:
    x.terkunci = kunci
    x.save(update_fields=["terkunci", "diubah_pada"])
    catat(request, "form.kiriman_dikunci" if kunci else "form.kiriman_dibuka", x.formulir,
          keterangan=f"Kiriman #{x.pk} {x.nama_pengisi}")  # fmt: skip


@transaction.atomic
def simpan_pemecah_seri(request, f: Formulir, nilai: dict[str, int | None]) -> None:
    for kunci, v in nilai.items():
        if v is None:
            PemecahSeri.objects.filter(formulir=f, kunci_subjek=kunci).delete()
        else:
            PemecahSeri.objects.update_or_create(formulir=f, kunci_subjek=kunci, defaults={"nilai": v})
    catat(request, "form.pemecah_seri", f, baru=dict(nilai.items()))


# --- Akses ---------------------------------------------------------------------------------------------------


def boleh_isi(user, f: Formulir) -> bool:
    if user is not None and user.is_authenticated and getattr(user, "superadmin", False):
        return True
    if f.akses == AksesForm.JURI:
        return user is not None and user.is_authenticated and getattr(user, "peran", "") == "JURI"
    return f.akses == AksesForm.PUBLIK


# --- Kiriman -------------------------------------------------------------------------------------------------


def _simpan_berkas(f: Formulir, berkas: dict) -> dict:
    hasil = {}
    folder = Path(settings.SIGAP_FOLDER_PRIVAT) / "form" / str(f.pk)
    folder.mkdir(parents=True, exist_ok=True)
    for kode, b in berkas.items():
        ext = Path(b.name).suffix.lower()
        nama = f"{uuid.uuid4().hex}{ext}"
        with open(folder / nama, "wb") as out:
            for potong in b.chunks():
                out.write(potong)
        hasil[kode] = {"nama": Path(b.name).name[:150], "file": nama, "ukuran": b.size}
    return hasil


def path_berkas(f: Formulir, nama_file: str) -> Path | None:
    if not re.fullmatch(r"[0-9a-f]{32}\.[a-z0-9]{1,5}", nama_file or ""):
        return None
    p = Path(settings.SIGAP_FOLDER_PRIVAT) / "form" / str(f.pk) / nama_file
    return p if p.is_file() else None


def kiriman_juri(f: Formulir, subjek: Subjek | None, nama: str):
    qs = Kiriman.objects.filter(formulir=f)
    if subjek is not None:
        qs = qs.filter(kontingen=subjek.kontingen, peserta=subjek.peserta)
    return [x for x in qs if x.nama_pengisi.casefold() == nama.casefold()]


def kirim(request, f: Formulir, data: dict, berkas: dict, nama_pengisi: str, subjek: Subjek | None,
          client_uuid: str | None = None, subjek_teks: str = "") -> tuple[Kiriman, bool]:  # fmt: skip
    """Simpan satu kiriman. Mengembalikan (kiriman, diganti). GagalForm bila ditolak."""
    user = getattr(request, "user", None)
    superadmin = bool(user and user.is_authenticated and getattr(user, "superadmin", False))
    try:
        cu = uuid.UUID(str(client_uuid)) if client_uuid else None
    except ValueError:
        cu = None
    if cu and (lama := Kiriman.semua.filter(client_uuid=cu).first()):
        return lama, False  # kiriman ganda (tombol ditekan dua kali / koneksi diulang)
    with transaction.atomic():
        f = Formulir.objects.select_for_update().get(pk=f.pk)  # urutkan kiriman per form
        if f.terkunci:
            raise GagalForm("Form sudah dikunci. Hubungi superadmin.")
        if not superadmin and not f.terbuka():
            raise GagalForm("Form sedang tidak dibuka.")
        if f.jenis_subjek != JenisSubjek.BEBAS and subjek is None:
            raise GagalForm("Pilih subjek yang dinilai.")
        sebelumnya = []
        if f.mode == ModeForm.PENILAIAN:
            sebelumnya = kiriman_juri(f, subjek, nama_pengisi)
        elif f.satu_per_subjek and subjek is not None:
            sebelumnya = list(Kiriman.objects.filter(formulir=f, kontingen=subjek.kontingen, peserta=subjek.peserta))
        if sebelumnya:
            lama = sebelumnya[-1]
            if lama.terkunci and not superadmin:
                raise GagalForm(
                    "Nilai untuk subjek ini dari juri dengan nama yang sama sudah dikirim dan tidak bisa diubah. "
                    "Hubungi superadmin bila perlu diperbaiki."
                    if f.mode == ModeForm.PENILAIAN
                    else "Subjek ini sudah punya kiriman. Hubungi superadmin bila perlu diperbaiki."
                )
            simpan_berkas = _simpan_berkas(f, berkas)
            lama.riwayat = [*lama.riwayat, {"data": lama.data, "dikirim_pada": lama.dikirim_pada.isoformat(),
                                            "nama_pengisi": lama.nama_pengisi}]  # fmt: skip
            lama.data = {
                **{k: v for k, v in lama.data.items() if isinstance(v, dict) and "file" in v},
                **data,
                **simpan_berkas,
            }
            lama.nama_pengisi = nama_pengisi
            lama.dikirim_pada = timezone.now()
            lama.terkunci = True
            lama.akun = user if user and user.is_authenticated else None
            if cu:
                lama.client_uuid = cu
            lama.save()
            catat(request, "form.kiriman_diganti", f, keterangan=f"{nama_pengisi} · {getattr(subjek, 'label', '')}"[:255],
                  nama_pelaku=nama_pengisi)  # fmt: skip
            return lama, True
        isian = {**data, **_simpan_berkas(f, berkas)}
        if subjek_teks:
            isian["_subjek"] = subjek_teks[:200]
        try:
            x = Kiriman.objects.create(
                formulir=f, kontingen=getattr(subjek, "kontingen", None), peserta=getattr(subjek, "peserta", None),
                nama_pengisi=nama_pengisi, akun=user if user and user.is_authenticated else None, data=isian,
                client_uuid=cu, ip=ip_klien(request), user_agent=user_agent(request), terkunci=True,
            )  # fmt: skip
        except IntegrityError:
            raise GagalForm("Kiriman ini sudah diterima.") from None
        catat(request, "form.kiriman_baru", f, keterangan=f"{nama_pengisi} · {getattr(subjek, 'label', '')}"[:255],
              nama_pelaku=nama_pengisi)  # fmt: skip
        return x, False


@transaction.atomic
def ubah_kiriman(request, x: Kiriman, data: dict, berkas: dict, nama_pengisi: str) -> None:
    """Superadmin mengubah isi kiriman (riwayat disimpan)."""
    lama = dict(x.data)
    x.riwayat = [*x.riwayat, {"data": lama, "dikirim_pada": x.dikirim_pada.isoformat(), "nama_pengisi": x.nama_pengisi,
                              "diubah_oleh": nama_pelaku(request)}]  # fmt: skip
    x.data = {**{k: v for k, v in lama.items() if isinstance(v, dict) and "file" in v or k == "_subjek"}, **data,
              **_simpan_berkas(x.formulir, berkas)}  # fmt: skip
    x.nama_pengisi = nama_pengisi
    x.save()
    catat(request, "form.kiriman_diubah", x.formulir, keterangan=f"Kiriman #{x.pk}", lama=lama, baru=x.data)


@transaction.atomic
def hapus_kiriman(request, x: Kiriman) -> None:
    x.hapus_lunak(oleh=nama_pelaku(request))
    catat(request, "form.kiriman_dihapus", x.formulir, keterangan=f"Kiriman #{x.pk} {x.nama_pengisi}")
