"""Kueri biodata untuk superadmin: pencarian, saringan, urutan, statistik dasbor."""

from __future__ import annotations

from dataclasses import dataclass, field

from django.db.models import Count, Exists, OuterRef, Q, QuerySet
from django.db.models.functions import TruncDate

from apps.inti.models import Tingkat
from apps.kontingen.models import URUTAN_TINGKAT, Kontingen

from . import nik as nik_mod
from .models import JenisPenanda, PenandaPeserta, Peran, Peserta

URUTAN = {
    "baru": ("-dibuat_pada", "-id"),
    "lama": ("dibuat_pada", "id"),
    "nama": ("nama_lengkap", "id"),
    "kontingen": ("kontingen__kode", "nama_lengkap"),
    "tingkat": ("tingkat", "kontingen__kode", "nama_lengkap"),
    "peran": ("peran", "nama_lengkap"),
    "lahir": ("-tanggal_lahir", "nama_lengkap"),
}


@dataclass
class Saringan:
    q: str = ""
    kontingen: str = ""
    tingkat: str = ""
    peran: str = ""
    jk: str = ""
    tanda: str = ""
    kegiatan: str = ""
    urut: str = "baru"
    aktif: list[str] = field(default_factory=list)

    @classmethod
    def dari_get(cls, get) -> Saringan:
        s = cls(
            q=get.get("q", "").strip()[:100],
            kontingen=get.get("kontingen", ""),
            tingkat=get.get("tingkat", ""),
            peran=get.get("peran", ""),
            jk=get.get("jk", ""),
            tanda=get.get("tanda", ""),
            kegiatan=get.get("kegiatan", ""),
            urut=get.get("urut", "baru") if get.get("urut") in URUTAN else "baru",
        )
        s.aktif = [k for k in ("q", "kontingen", "tingkat", "peran", "jk", "tanda", "kegiatan") if getattr(s, k)]
        return s


def ada_tanda_aktif():
    return Exists(PenandaPeserta.objects.filter(peserta=OuterRef("pk"), diabaikan_pada__isnull=True))


def saring(s: Saringan, qs: QuerySet | None = None) -> QuerySet:
    qs = (qs if qs is not None else Peserta.objects.all()).select_related("kontingen")
    if s.q:
        teks = "".join(s.q.split())
        if teks.isdigit() and len(teks) == 16:
            qs = qs.filter(nik_hash=nik_mod.hash_nik(teks))
        elif teks.isdigit() and len(teks) == 4:
            qs = qs.filter(nik_akhir4=teks)
        else:
            kode = s.q.upper().replace(" ", "")
            if not kode.startswith("SJ-") and len(kode) == 6 and kode.isalnum():
                kode = "SJ-" + kode
            qs = qs.filter(Q(nama_lengkap__icontains=s.q) | Q(kode_pendaftaran__iexact=kode))
    if s.kontingen.isdigit():
        qs = qs.filter(kontingen_id=int(s.kontingen))
    if s.tingkat in Tingkat.values:
        qs = qs.filter(tingkat=s.tingkat)
    if s.peran in Peran.values:
        qs = qs.filter(peran=s.peran)
    if s.jk in ("L", "P"):
        qs = qs.filter(jenis_kelamin=s.jk)
    if s.tanda == "ada":
        qs = qs.filter(ada_tanda_aktif())
    elif s.tanda == "tidak":
        qs = qs.exclude(ada_tanda_aktif())
    elif s.tanda in JenisPenanda.values:
        qs = qs.filter(penanda__jenis=s.tanda, penanda__diabaikan_pada__isnull=True)
    if s.kegiatan.isdigit():
        qs = qs.filter(kegiatan__id=int(s.kegiatan))
    elif s.kegiatan == "kosong":
        qs = qs.filter(kegiatan__isnull=True)
    elif s.kegiatan == "bentrok":
        from apps.absensi.jadwal import peserta_bentrok

        qs = qs.filter(pk__in=list(peserta_bentrok()))
    return qs.order_by(*URUTAN[s.urut]).distinct()


def statistik() -> dict:
    qs = Peserta.objects.all()
    per_tingkat = dict(qs.values_list("tingkat").annotate(n=Count("id")))
    per_peran = dict(qs.values_list("peran").annotate(n=Count("id")))
    per_hari = list(qs.annotate(hari=TruncDate("dibuat_pada")).values("hari").annotate(n=Count("id")).order_by("hari"))
    maks_hari = max((h["n"] for h in per_hari), default=0)
    for h in per_hari:
        h["persen"] = round(h["n"] * 100 / maks_hari) if maks_hari else 0
    return {
        "total": qs.count(),
        "per_tingkat": [(t.value, t.label, per_tingkat.get(t.value, 0)) for t in Tingkat],
        "per_peran": [(p.value, p.label, per_peran.get(p.value, 0)) for p in Peran],
        "per_hari": per_hari,
        "dengan_tanda": qs.filter(ada_tanda_aktif()).count(),
        "tanpa_foto": qs.filter(foto_path="").count(),
    }


def tabel_kontingen() -> list[dict]:
    """Kuota vs terisi per kontingen, jumlah per peran, jumlah orang bertanda."""
    hitung = {Peran.PESERTA: "n_peserta", Peran.PIMPINAN_KONTINGEN: "n_pimpinan",
              Peran.PEMBINA_PENDAMPING: "n_pembina", Peran.PENINJAU: "n_peninjau"}  # fmt: skip
    anotasi = {nama: Count("peserta", filter=Q(peserta__dihapus_pada__isnull=True, peserta__peran=p))
               for p, nama in hitung.items()}  # fmt: skip
    anotasi["terisi"] = Count("peserta", filter=Q(peserta__dihapus_pada__isnull=True))
    baris = list(Kontingen.objects.annotate(**anotasi).order_by(URUTAN_TINGKAT, "kode"))
    bertanda = dict(Peserta.objects.filter(ada_tanda_aktif()).values_list("kontingen_id").annotate(n=Count("id")))
    hasil = []
    for k in baris:
        sisa = k.kuota - k.terisi
        # merah = lebih dari kuota, hijau = tepat sesuai kuota, kuning = hampir penuh (>= 90%).
        if k.kuota and k.terisi > k.kuota:
            warna = "merah"
        elif k.kuota and k.terisi == k.kuota:
            warna = "hijau"
        elif k.kuota and k.terisi >= k.kuota * 0.9:
            warna = "kuning"
        else:
            warna = "abu"
        hasil.append({"k": k, "sisa": sisa, "lebih": max(0, -sisa), "warna": warna, "bertanda": bertanda.get(k.pk, 0),
                      "persen": min(100, round(k.terisi * 100 / k.kuota)) if k.kuota else 0})  # fmt: skip
    return hasil
