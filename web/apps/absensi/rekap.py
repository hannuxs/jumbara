"""Rekap kehadiran dan poin kehadiran (docs/15-REKAP-POIN.md).

Poin per sesi (titik absen) s untuk kontingen k dengan kuota q:
    hadir    = jumlah orang kontingen k yang tercatat di s
    dihitung = min(hadir, q)   bila pengaturan poin.batasi_ke_kuota (bawaan ya), selain itu hadir
    absen    = max(q - hadir, 0)
    poin     = dihitung - absen
Kuota kosong: poin = hadir (tanpa pengurangan) + peringatan "kuota belum diatur".
Poin kehadiran kegiatan = jumlah poin semua sesi kegiatan itu pada tingkat kontingen (atau titik SEMUA).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from django.db.models import Count

from apps.biodata.models import Peserta
from apps.inti import pengaturan
from apps.kontingen.models import URUTAN_TINGKAT, Kontingen

from .models import Kegiatan, Kehadiran, KuotaKegiatan, TingkatTitik, TitikAbsen

KODE_DAFTAR_ULANG = "daftar-ulang"


@dataclass
class PoinSesi:
    hadir: int
    kuota: int | None
    dihitung: int
    absen: int
    poin: int
    lebih: bool  # hadir melebihi kuota

    @property
    def kuota_kosong(self) -> bool:
        return self.kuota is None


def hitung_poin_sesi(hadir: int, kuota: int | None, batasi: bool = True) -> PoinSesi:
    if kuota is None:
        return PoinSesi(hadir, None, hadir, 0, hadir, False)
    dihitung = min(hadir, kuota) if batasi else hadir
    absen = max(kuota - hadir, 0)
    return PoinSesi(hadir, kuota, dihitung, absen, dihitung - absen, hadir > kuota)


def batasi_ke_kuota() -> bool:
    return bool(pengaturan.ambil("poin.batasi_ke_kuota", True))


class PetaKuota:
    """Kuota per (kegiatan, kontingen): nilai khusus kontingen menimpa kuota bawaan kegiatan."""

    def __init__(self):
        self.bawaan = dict(Kegiatan.objects.values_list("id", "kuota_default"))
        self.khusus = {
            (kg, kt): q
            for kg, kt, q in KuotaKegiatan.objects.exclude(kontingen=None).values_list(
                "kegiatan_id", "kontingen_id", "kuota"
            )
        }

    def kuota(self, kegiatan_id: int | None, kontingen_id: int) -> int | None:
        if kegiatan_id is None:
            return None
        return self.khusus.get((kegiatan_id, kontingen_id), self.bawaan.get(kegiatan_id))


def hitungan_hadir(titik_ids=None) -> dict[tuple[int, int], int]:
    """{(titik_id, kontingen_id): jumlah hadir} dari kehadiran aktif."""
    qs = Kehadiran.objects.all()
    if titik_ids is not None:
        qs = qs.filter(titik_absen_id__in=list(titik_ids))
    return {
        (t, k): n
        for t, k, n in qs.values_list("titik_absen_id", "peserta__kontingen_id").annotate(n=Count("id")).order_by()
    }


def titik_untuk_tingkat(titik_qs, tingkat: str):
    return [t for t in titik_qs if t.tingkat in (tingkat, TingkatTitik.SEMUA)]


def kontingen_berlaku(titik: TitikAbsen, daftar_kontingen) -> list[Kontingen]:
    if titik.tingkat == TingkatTitik.SEMUA:
        return list(daftar_kontingen)
    return [k for k in daftar_kontingen if k.tingkat == titik.tingkat]


# --- Poin kehadiran per kegiatan --------------------------------------------------------


@dataclass
class BarisPoin:
    kontingen: Kontingen
    sesi: list[tuple[TitikAbsen, PoinSesi]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(p.poin for _, p in self.sesi)

    @property
    def total_hadir(self) -> int:
        return sum(p.hadir for _, p in self.sesi)

    @property
    def ada_kuota_kosong(self) -> bool:
        return any(p.kuota_kosong for _, p in self.sesi)


def tabel_poin_kegiatan(kegiatan: Kegiatan, tingkat: str) -> tuple[list[TitikAbsen], list[BarisPoin]]:
    """Untuk satu kegiatan dan tingkat: sesi (titik) dan poin setiap kontingen tingkat itu."""
    titik = [
        t
        for t in TitikAbsen.objects.filter(kegiatan=kegiatan, hitung_poin=True).order_by("tanggal", "mulai", "kode")
        if t.tingkat in (tingkat, TingkatTitik.SEMUA)
    ]
    kontingen = list(Kontingen.objects.filter(tingkat=tingkat).order_by("kode"))
    hadir = hitungan_hadir([t.pk for t in titik])
    peta = PetaKuota()
    batasi = batasi_ke_kuota()
    baris = []
    for k in kontingen:
        b = BarisPoin(k)
        for t in titik:
            b.sesi.append((t, hitung_poin_sesi(hadir.get((t.pk, k.pk), 0), peta.kuota(kegiatan.pk, k.pk), batasi)))
        baris.append(b)
    return titik, baris


def poin_kehadiran(kegiatan_kode: str, kontingen: Kontingen) -> dict:
    """Untuk kolom otomatis form penilaian: poin_kehadiran, jumlah_hadir, kuota (Tahap 4)."""
    kegiatan = Kegiatan.objects.filter(kode=kegiatan_kode).first()
    if kegiatan is None:
        return {"poin_kehadiran": 0, "jumlah_hadir": 0, "kuota": None}
    _, baris = tabel_poin_kegiatan(kegiatan, kontingen.tingkat)
    b = next((x for x in baris if x.kontingen.pk == kontingen.pk), None)
    kuota = PetaKuota().kuota(kegiatan.pk, kontingen.pk)
    if b is None:
        return {"poin_kehadiran": 0, "jumlah_hadir": 0, "kuota": kuota}
    return {"poin_kehadiran": b.total, "jumlah_hadir": b.total_hadir, "kuota": kuota}


# --- Rekap per tingkat --------------------------------------------------------------------


def rekap_tingkat(tingkat: str) -> list[dict]:
    """Setiap titik pada tingkat itu: hadir, kontingen hadir, persen terhadap total kuota."""
    titik = titik_untuk_tingkat(
        TitikAbsen.objects.select_related("kegiatan").order_by("tanggal", "mulai", "kode"), tingkat
    )
    kontingen = list(Kontingen.objects.filter(tingkat=tingkat))
    hadir = hitungan_hadir([t.pk for t in titik])
    peta = PetaKuota()
    hasil = []
    for t in titik:
        jumlah = sum(hadir.get((t.pk, k.pk), 0) for k in kontingen)
        kontingen_hadir = sum(1 for k in kontingen if hadir.get((t.pk, k.pk), 0))
        if t.kegiatan_id and t.kegiatan.kode == KODE_DAFTAR_ULANG:
            kuota_total = sum(k.kuota for k in kontingen)
        else:
            nilai = [peta.kuota(t.kegiatan_id, k.pk) for k in kontingen]
            kuota_total = sum(v for v in nilai if v) if any(v is not None for v in nilai) else None
        hasil.append({
            "titik": t, "hadir": jumlah, "kontingen_hadir": kontingen_hadir, "kontingen_total": len(kontingen),
            "kuota": kuota_total, "persen": round(jumlah * 100 / kuota_total) if kuota_total else None,
        })  # fmt: skip
    return hasil


# --- Rekap per titik ----------------------------------------------------------------------


def rekap_titik(titik: TitikAbsen) -> dict:
    hadir_list = list(
        Kehadiran.objects.filter(titik_absen=titik)
        .select_related("peserta__kontingen")
        .order_by("peserta__kontingen__kode", "peserta__nama_lengkap")
    )
    kontingen = kontingen_berlaku(titik, Kontingen.objects.order_by(URUTAN_TINGKAT, "kode"))
    per_k = defaultdict(int)
    for k in hadir_list:
        per_k[k.peserta.kontingen_id] += 1
    peta = PetaKuota()
    daftar_ulang = bool(titik.kegiatan_id and titik.kegiatan.kode == KODE_DAFTAR_ULANG)
    batasi = batasi_ke_kuota()
    baris = []
    for k in kontingen:
        kuota = k.kuota if daftar_ulang else peta.kuota(titik.kegiatan_id, k.pk)
        p = hitung_poin_sesi(per_k.get(k.pk, 0), kuota, batasi)
        status = (
            "belum"
            if p.hadir == 0
            else ("kurang" if p.kuota and p.hadir < p.kuota else ("lebih" if p.lebih else "cukup"))
        )
        baris.append({"k": k, "p": p, "status": status})
    return {"hadir": hadir_list, "kontingen": baris}


# --- Rekap per kontingen ------------------------------------------------------------------


def rekap_kontingen(k: Kontingen) -> dict:
    titik = titik_untuk_tingkat(
        TitikAbsen.objects.select_related("kegiatan").order_by("tanggal", "mulai", "kode"), k.tingkat
    )
    hadir = hitungan_hadir([t.pk for t in titik])
    peta = PetaKuota()
    batasi = batasi_ke_kuota()
    baris = []
    for t in titik:
        du = bool(t.kegiatan_id and t.kegiatan.kode == KODE_DAFTAR_ULANG)
        kuota = k.kuota if du else peta.kuota(t.kegiatan_id, k.pk)
        baris.append({"titik": t, "p": hitung_poin_sesi(hadir.get((t.pk, k.pk), 0), kuota, batasi), "daftar_ulang": du})
    return {"baris": baris, "daftar_ulang": daftar_ulang_kontingen(k)}


def daftar_ulang_kontingen(k: Kontingen) -> dict:
    titik_du = TitikAbsen.objects.filter(kegiatan__kode=KODE_DAFTAR_ULANG)
    sudah_ids = set(
        Kehadiran.objects.filter(titik_absen__in=titik_du, peserta__kontingen=k).values_list("peserta_id", flat=True)
    )
    anggota = list(Peserta.objects.filter(kontingen=k).order_by("peran", "nama_lengkap"))
    return {
        "sudah": [p for p in anggota if p.pk in sudah_ids],
        "belum": [p for p in anggota if p.pk not in sudah_ids],
        "total": len(anggota),
    }


def rekap_daftar_ulang() -> list[dict]:
    titik_du = TitikAbsen.objects.filter(kegiatan__kode=KODE_DAFTAR_ULANG)
    sudah = dict(
        Kehadiran.objects.filter(titik_absen__in=titik_du)
        .values_list("peserta__kontingen_id")
        .annotate(n=Count("peserta", distinct=True))
        .order_by()
    )
    biodata = dict(Peserta.objects.values_list("kontingen_id").annotate(n=Count("id")).order_by())
    hasil = []
    for k in Kontingen.objects.order_by(URUTAN_TINGKAT, "kode"):
        total = biodata.get(k.pk, 0)
        s = sudah.get(k.pk, 0)
        hasil.append({"k": k, "biodata": total, "sudah": s, "belum": total - s})
    return hasil


# --- Rekap harian ---------------------------------------------------------------------------


def rekap_harian(tanggal) -> list[dict]:
    """Per tingkat: tabel kontingen x titik pada tanggal itu (hadir/kuota)."""
    titik_hari = list(TitikAbsen.objects.filter(tanggal=tanggal).select_related("kegiatan").order_by("mulai", "kode"))
    hadir = hitungan_hadir([t.pk for t in titik_hari])
    peta = PetaKuota()
    batasi = batasi_ke_kuota()
    hasil = []
    for tingkat in ("MULA", "MADYA", "WIRA"):
        titik = titik_untuk_tingkat(titik_hari, tingkat)
        if not titik:
            continue
        baris = []
        for k in Kontingen.objects.filter(tingkat=tingkat).order_by("kode"):
            sel = []
            for t in titik:
                du = bool(t.kegiatan_id and t.kegiatan.kode == KODE_DAFTAR_ULANG)
                kuota = k.kuota if du else peta.kuota(t.kegiatan_id, k.pk)
                sel.append(hitung_poin_sesi(hadir.get((t.pk, k.pk), 0), kuota, batasi))
            baris.append({"k": k, "sel": sel})
        hasil.append({"tingkat": tingkat, "titik": titik, "baris": baris})
    return hasil
