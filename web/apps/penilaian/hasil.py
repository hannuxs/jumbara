"""Tabel hasil form penilaian (mode 2): agregasi antarjuri, kolom otomatis, rumus, REF, peringkat."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from django.db.models import Q

from apps.absensi.models import Kegiatan
from apps.absensi.rekap import PetaKuota, tabel_poin_kegiatan
from apps.biodata.models import Peserta
from apps.kontingen.models import Kontingen

from . import rumus as r
from .models import (
    JENIS_ANGKA,
    Agregasi,
    ArahUrut,
    Formulir,
    JenisKolom,
    JenisSubjek,
    Kiriman,
    Kolom,
    ModeForm,
    PemecahSeri,
    StatusForm,
    TingkatForm,
)

BAWAAN = ("poin_kehadiran", "jumlah_hadir", "kuota", "jumlah_juri")
SUMBER_ANJANGSANA = "anjangsana"
KOLOM_ANJANGSANA = ("rata_rata", "jumlah_review", "tamu_berbeda", "jumlah_kunjungan", "peringkat", "peringkat_gabungan")
KOLOM_PERINGKAT = "peringkat"


# --- Subjek ------------------------------------------------------------------------------------------


@dataclass
class Subjek:
    kunci: str
    label: str
    tingkat: str
    kontingen: Kontingen | None = None
    peserta: Peserta | None = None

    @property
    def kontingen_id(self) -> int | None:
        return self.kontingen.pk if self.kontingen else (self.peserta.kontingen_id if self.peserta else None)


def daftar_subjek(f: Formulir) -> list[Subjek]:
    if f.jenis_subjek == JenisSubjek.KONTINGEN:
        qs = f.subjek_kontingen.all() if f.pk and f.subjek_kontingen.exists() else Kontingen.objects.all()
        if f.tingkat != TingkatForm.SEMUA:
            qs = qs.filter(tingkat=f.tingkat)
        return [Subjek(f"K{k.pk}", f"{k.nama}", k.tingkat, kontingen=k) for k in qs.order_by("kode")]
    if f.jenis_subjek == JenisSubjek.PESERTA:
        qs = f.subjek_peserta.all() if f.pk and f.subjek_peserta.exists() else Peserta.objects.all()
        if f.tingkat != TingkatForm.SEMUA:
            qs = qs.filter(tingkat=f.tingkat)
        qs = qs.select_related("kontingen").order_by("kontingen__kode", "nama_lengkap")
        return [Subjek(f"P{p.pk}", f"{p.nama_lengkap} ({p.kontingen.nama})", p.tingkat, peserta=p) for p in qs]
    return []


def subjek_dari_kunci(f: Formulir, kunci: str) -> Subjek | None:
    return next((s for s in daftar_subjek(f) if s.kunci == kunci), None)


# --- Nilai angka dari isian --------------------------------------------------------------------------


def nilai_angka(kolom: Kolom, isi) -> float | None:
    """Ubah isian kolom menjadi angka untuk rumus (None bila kosong/bukan angka)."""
    if isi is None or isi == "" or isi == []:
        return None
    if kolom.jenis == JenisKolom.YA_TIDAK:
        return 1.0 if isi in (True, "ya", "YA", 1, "1") else 0.0
    if kolom.jenis in (JenisKolom.ANGKA, JenisKolom.SKALA, JenisKolom.PILIHAN, JenisKolom.DROPDOWN):
        try:
            return float(str(isi).replace(",", "."))
        except ValueError:
            return None
    return None


def kolom_angka(kolom: Kolom) -> bool:
    """Kolom isian yang bisa dipakai di rumus."""
    if kolom.jenis in JENIS_ANGKA:
        return True
    if kolom.jenis in (JenisKolom.PILIHAN, JenisKolom.DROPDOWN):
        pilihan = kolom.atur("pilihan", [])
        return bool(pilihan) and all(nilai_angka(kolom, p) is not None for p in pilihan)
    return False


# --- Peringkat ---------------------------------------------------------------------------------------------


def hitung_peringkat(
    nilai: dict[str, float | None], naik: bool, pemecah: dict[str, int] | None = None
) -> tuple[dict[str, int], set[str]]:
    """Peringkat kompetisi (1, 2, 2, 4). Nilai kosong tidak diberi peringkat. Pemecah seri: kecil = di atas."""
    pemecah = pemecah or {}
    isi = [(k, v) for k, v in nilai.items() if v is not None]
    tanpa = float("inf")
    isi.sort(key=lambda kv: ((kv[1] if naik else -kv[1]), pemecah.get(kv[0], tanpa)))
    peringkat: dict[str, int] = {}
    sebelum = None
    for i, (k, v) in enumerate(isi, start=1):
        kunci = (round(v, 9), pemecah.get(k, tanpa))
        if kunci != sebelum:
            nomor = i
            sebelum = kunci
        peringkat[k] = nomor
    hitung = defaultdict(int)
    for p in peringkat.values():
        hitung[p] += 1
    seri = {k for k, p in peringkat.items() if hitung[p] > 1}
    return peringkat, seri


# --- Tabel hasil ------------------------------------------------------------------------------------------


@dataclass
class BarisHasil:
    subjek: Subjek
    nilai: dict[str, float | None] = field(default_factory=dict)
    kiriman: list[Kiriman] = field(default_factory=list)
    peringkat: int | None = None
    seri: bool = False
    pemecah: int | None = None
    peringatan: list[str] = field(default_factory=list)

    @property
    def jumlah_juri(self) -> int:
        return len(self.kiriman)

    @property
    def belum_dinilai(self) -> bool:
        return not self.kiriman


@dataclass
class TabelHasil:
    formulir: Formulir
    kolom: list[Kolom]
    baris: list[BarisHasil]
    bawaan_tampil: list[str]
    galat: list[str] = field(default_factory=list)

    def baris_subjek(self, kunci: str) -> BarisHasil | None:
        return next((b for b in self.baris if b.subjek.kunci == kunci), None)


class Penghitung:
    """Menghitung tabel satu atau beberapa form (dengan cache dan deteksi REF melingkar)."""

    def __init__(self):
        self._cache: dict[int, TabelHasil] = {}
        self._sedang: list[int] = []
        self._anjangsana: dict[str, dict] = {}

    # REF ---------------------------------------------------------------------------------------------
    def cari_form(self, slug: str, tingkat: str | None, wajib_tingkat: bool) -> Formulir | None:
        calon = list(
            Formulir.objects.filter(Q(slug=slug) | Q(kunci_ref=slug), mode=ModeForm.PENILAIAN)
            .exclude(status=StatusForm.ARSIP)
            .order_by("pk")
        )
        tepat = [f for f in calon if f.slug == slug]
        if tepat and not wajib_tingkat:
            return tepat[0]
        if tingkat:
            sama = [f for f in calon if f.tingkat == tingkat]
            if sama:
                return sama[0]
        if wajib_tingkat:
            return None
        semua = [f for f in calon if f.tingkat == TingkatForm.SEMUA]
        if semua:
            return semua[0]
        return calon[0] if len(calon) == 1 else None

    def nilai_ref(self, slug: str, kode: str, tingkat_ini: bool, subjek: Subjek, peringatan: list[str]) -> float | None:
        if slug == SUMBER_ANJANGSANA:
            return self._nilai_anjangsana(kode, subjek)
        f = self.cari_form(slug, subjek.tingkat, tingkat_ini)
        if f is None:
            peringatan.append(f'REF: form "{slug}" untuk tingkat {subjek.tingkat.title()} tidak ditemukan.')
            return None
        if f.pk in self._sedang:
            peringatan.append(f'REF melingkar ke form "{f.slug}".')
            return None
        t = self.tabel(f)
        b = t.baris_subjek(subjek.kunci)
        if b is None:
            return None
        if kode == KOLOM_PERINGKAT and kode not in b.nilai:
            return None if b.peringkat is None else float(b.peringkat)
        return b.nilai.get(kode)

    def _nilai_anjangsana(self, kode: str, subjek: Subjek) -> float | None:
        from apps.anjangsana.services import peringkat as peringkat_anjangsana

        if subjek.kontingen is None:
            return None
        kunci = subjek.tingkat
        if kunci not in self._anjangsana:
            self._anjangsana[kunci] = {h["k"].pk: h for h in peringkat_anjangsana(kunci)}
        if "*" not in self._anjangsana:
            self._anjangsana["*"] = {h["k"].pk: h for h in peringkat_anjangsana(None)}
        h = self._anjangsana[kunci].get(subjek.kontingen.pk)
        if h is None:
            return None
        if kode == "peringkat":
            return float(h["peringkat"])
        if kode == "peringkat_gabungan":
            g = self._anjangsana["*"].get(subjek.kontingen.pk)
            return float(g["peringkat"]) if g else None
        v = h.get(kode)
        return None if v is None else float(v)

    # Tabel ----------------------------------------------------------------------------------------------
    def tabel(self, f: Formulir) -> TabelHasil:
        if f.pk in self._cache:
            return self._cache[f.pk]
        self._sedang.append(f.pk)
        try:
            t = self._hitung(f)
        finally:
            self._sedang.pop()
        self._cache[f.pk] = t
        return t

    def _hitung(self, f: Formulir) -> TabelHasil:
        kolom = list(f.kolom.all())
        per_kode = {k.kode: k for k in kolom}
        subjek = daftar_subjek(f)
        galat: list[str] = []

        kiriman = defaultdict(list)
        for x in Kiriman.objects.filter(formulir=f).order_by("dikirim_pada", "pk"):
            kiriman[x.kunci_subjek].append(x)
        baris = {s.kunci: BarisHasil(s, kiriman=kiriman.get(s.kunci, [])) for s in subjek}

        # 1. Isian angka: agregasi antarjuri.
        for k in kolom:
            if not k.diisi or not kolom_angka(k):
                continue
            for b in baris.values():
                angka = [nilai_angka(k, x.data.get(k.kode)) for x in b.kiriman]
                angka = [a for a in angka if a is not None]
                if not angka:
                    b.nilai[k.kode] = None
                elif f.agregasi == Agregasi.JUMLAH:
                    b.nilai[k.kode] = sum(angka)
                elif f.agregasi == Agregasi.TERAKHIR:
                    b.nilai[k.kode] = angka[-1]
                else:
                    b.nilai[k.kode] = sum(angka) / len(angka)

        # 2. Kolom bawaan dari sistem.
        hadir = self._kehadiran(f, subjek)
        for b in baris.values():
            dari_absen = hadir.get(b.subjek.kontingen_id, {}) if b.subjek.kontingen else {}
            b.nilai.setdefault("poin_kehadiran", dari_absen.get("poin_kehadiran", 0.0 if f.kegiatan_id else None))
            b.nilai.setdefault("jumlah_hadir", dari_absen.get("jumlah_hadir", 0.0 if f.kegiatan_id else None))
            b.nilai.setdefault("kuota", dari_absen.get("kuota"))
            b.nilai.setdefault("jumlah_juri", float(len(b.kiriman)))
        for k in kolom:
            if k.jenis == JenisKolom.OTOMATIS:
                sumber = k.atur("sumber", "poin_kehadiran")
                for b in baris.values():
                    b.nilai[k.kode] = b.nilai.get(sumber)

        # 3. Rumus dan kolom peringkat sesuai urutan ketergantungan.
        pohon: dict[str, r.Simpul] = {}
        bergantung: dict[str, set[str]] = {}
        for k in kolom:
            if k.jenis == JenisKolom.RUMUS:
                try:
                    pohon[k.kode] = r.urai(k.atur("rumus", ""))
                    bergantung[k.kode] = r.rujukan(pohon[k.kode]).kolom
                except r.GalatRumus as e:
                    galat.append(f"Rumus [{k.kode}]: {e}")
            elif k.jenis == JenisKolom.PERINGKAT:
                bergantung[k.kode] = {k.atur("dasar", "")}
        try:
            urutan = r.urutan_hitung(bergantung)
        except r.GalatRumus as e:
            galat.append(str(e))
            urutan = []
        for kode in urutan:
            k = per_kode[kode]
            if k.jenis == JenisKolom.PERINGKAT:
                naik = k.atur("arah", ArahUrut.TURUN) == ArahUrut.NAIK
                p, _ = hitung_peringkat({kk: b.nilai.get(k.atur("dasar")) for kk, b in baris.items()}, naik)
                for kk, b in baris.items():
                    b.nilai[kode] = float(p[kk]) if kk in p else None
                continue
            if kode not in pohon:
                continue
            cache_peringkat: dict[tuple[str, bool], dict[str, int]] = {}
            for b in baris.values():
                b.nilai[kode] = r.hitung_aman(pohon[kode], self._konteks(b, baris, cache_peringkat), kode)

        # 4. Peringkat akhir form (kolom urut + pemecah seri).
        kolom_urut = f.kolom_urut if f.kolom_urut else ""
        if kolom_urut:
            pemecah = dict(PemecahSeri.objects.filter(formulir=f).values_list("kunci_subjek", "nilai"))
            p, seri = hitung_peringkat(
                {kk: b.nilai.get(kolom_urut) for kk, b in baris.items()}, f.arah_urut == ArahUrut.NAIK, pemecah
            )
            for kk, b in baris.items():
                b.peringkat = p.get(kk)
                b.seri = kk in seri
                b.pemecah = pemecah.get(kk)

        dipakai = set()
        for kode in pohon:
            dipakai |= bergantung.get(kode, set())
        bawaan_tampil = [
            x for x in BAWAAN if x in dipakai or (x in ("poin_kehadiran", "jumlah_hadir") and f.kegiatan_id)
        ]
        if "jumlah_juri" not in bawaan_tampil:
            bawaan_tampil.append("jumlah_juri")
        bawaan_tampil = [x for x in bawaan_tampil if x not in per_kode]
        return TabelHasil(f, kolom, list(baris.values()), bawaan_tampil, galat)

    def _konteks(self, b: BarisHasil, baris: dict[str, BarisHasil], cache_peringkat) -> r.Konteks:
        def peringkat(kode: str, naik: bool) -> float | None:
            if (kode, naik) not in cache_peringkat:
                cache_peringkat[(kode, naik)], _ = hitung_peringkat(
                    {k: x.nilai.get(kode) for k, x in baris.items()}, naik
                )
            p = cache_peringkat[(kode, naik)].get(b.subjek.kunci)
            return None if p is None else float(p)

        return r.Konteks(
            nilai=lambda kode: b.nilai.get(kode),
            ref=lambda slug, kode, ti: self.nilai_ref(slug, kode, ti, b.subjek, b.peringatan),
            peringkat=peringkat,
            peringatan=b.peringatan,
        )

    def _kehadiran(self, f: Formulir, subjek: list[Subjek]) -> dict[int, dict]:
        """poin_kehadiran, jumlah_hadir, kuota per kontingen untuk kegiatan form (sekali per tingkat)."""
        if not f.kegiatan_id or not any(s.kontingen for s in subjek):
            return {}
        kegiatan = Kegiatan.objects.get(pk=f.kegiatan_id)
        peta = PetaKuota()
        hasil: dict[int, dict] = {}
        for tingkat in {s.tingkat for s in subjek if s.kontingen}:
            _, baris = tabel_poin_kegiatan(kegiatan, tingkat)
            for b in baris:
                hasil[b.kontingen.pk] = {
                    "poin_kehadiran": float(b.total),
                    "jumlah_hadir": float(b.total_hadir),
                    "kuota": None if (q := peta.kuota(kegiatan.pk, b.kontingen.pk)) is None else float(q),
                }
        return hasil


def tabel_hasil(f: Formulir) -> TabelHasil:
    return Penghitung().tabel(f)


# --- Validasi rumus saat disimpan -----------------------------------------------------------------------


def nama_tersedia(f: Formulir, kecuali: str | None = None) -> dict[str, str]:
    """Nama yang boleh dipakai di [..] pada form ini: kode -> keterangan."""
    hasil = {}
    for k in f.kolom.all():
        if k.kode == kecuali:
            continue
        if (k.diisi and kolom_angka(k)) or k.dihitung:
            hasil[k.kode] = k.label
    for b in BAWAAN:
        hasil.setdefault(b, {"poin_kehadiran": "Poin kehadiran (otomatis)", "jumlah_hadir": "Jumlah hadir (otomatis)",
                             "kuota": "Kuota kegiatan (otomatis)", "jumlah_juri": "Jumlah juri (otomatis)"}[b])  # fmt: skip
    return hasil


def kolom_sumber(f: Formulir) -> set[str]:
    """Kode yang bisa ditarik form lain lewat REF dari form f."""
    nama = set(nama_tersedia(f))
    nama.add(KOLOM_PERINGKAT)
    return nama


def validasi_rumus(f: Formulir, kode: str, teks: str) -> r.Simpul:
    """Galat (GalatRumus) bila: tulisan salah, kolom tidak ada/bukan angka, melingkar, REF tidak ada/melingkar."""
    pohon = r.urai(teks)
    ruj = r.rujukan(pohon)
    tersedia = nama_tersedia(f, kecuali=None)
    teks_kolom = {k.kode for k in f.kolom.all() if k.diisi and not kolom_angka(k)}
    for nama in sorted(ruj.kolom):
        if nama == kode:
            raise r.GalatRumus(f"Rumus [{kode}] tidak boleh memakai dirinya sendiri.")
        if nama in teks_kolom:
            raise r.GalatRumus(f"Kolom [{nama}] berisi teks/tanggal/file, tidak bisa dihitung.")
        if nama not in tersedia:
            saran = ", ".join(f"[{x}]" for x in list(tersedia)[:8])
            raise r.GalatRumus(f"Kolom [{nama}] tidak ada di form ini. Yang tersedia: {saran}.")
    # Melingkar di dalam form.
    bergantung: dict[str, set[str]] = {}
    for k in f.kolom.all():
        if k.kode == kode:
            continue
        if k.jenis == JenisKolom.RUMUS:
            try:
                bergantung[k.kode] = r.rujukan(r.urai(k.atur("rumus", ""))).kolom
            except r.GalatRumus:
                bergantung[k.kode] = set()
        elif k.jenis == JenisKolom.PERINGKAT:
            bergantung[k.kode] = {k.atur("dasar", "")}
    bergantung[kode] = ruj.kolom
    r.urutan_hitung(bergantung)
    # REF ke form lain.
    for slug, kolom_ref, _tingkat_ini in ruj.ref:
        if slug == SUMBER_ANJANGSANA:
            if kolom_ref not in KOLOM_ANJANGSANA:
                raise r.GalatRumus(f'REF("anjangsana", ...) hanya: {", ".join(KOLOM_ANJANGSANA)}.')
            continue
        calon = list(Formulir.objects.filter(Q(slug=slug) | Q(kunci_ref=slug), mode=ModeForm.PENILAIAN))
        calon = [c for c in calon if c.pk != f.pk]
        if not calon:
            raise r.GalatRumus(f'REF: form penilaian "{slug}" tidak ditemukan (cek slug atau kunci REF).')
        for c in calon:
            if kolom_ref not in kolom_sumber(c):
                raise r.GalatRumus(f'REF: kolom [{kolom_ref}] tidak ada di form "{c.slug}".')
        if _mencapai(calon, f, set()):
            raise r.GalatRumus(f'REF melingkar: form "{slug}" (langsung atau tidak) menarik data dari form ini.')
    return pohon


def _mencapai(calon: list[Formulir], target: Formulir, dilihat: set[int]) -> bool:
    """Apakah salah satu form calon (lewat REF berantai) menarik data dari form target."""
    kunci_target = {target.slug, target.kunci_ref} - {""}
    for c in calon:
        if c.pk in dilihat:
            continue
        dilihat.add(c.pk)
        for k in c.kolom.filter(jenis=JenisKolom.RUMUS):
            try:
                refs = r.rujukan(r.urai(k.atur("rumus", ""))).ref
            except r.GalatRumus:
                continue
            for slug, _, _ in refs:
                if slug in kunci_target:
                    return True
                lanjut = list(Formulir.objects.filter(Q(slug=slug) | Q(kunci_ref=slug), mode=ModeForm.PENILAIAN))
                if _mencapai(lanjut, target, dilihat):
                    return True
    return False
