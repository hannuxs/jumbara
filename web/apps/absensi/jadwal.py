"""Jadwal kegiatan untuk pilihan kegiatan di form biodata: sesi per tingkat dan deteksi bentrok.

Sumber jadwal = titik absen (tanggal, mulai, selesai) yang terhubung ke kegiatan, sehingga mengubah jadwal
cukup dari halaman Titik absen. Titik tanpa jam selesai ("08.00-selesai" di jadwal panitia) dianggap selesai
pada pengaturan `kegiatan.selesai_bawaan` (bawaan 12.00) atau 2 jam setelah mulai bila mulai sesudahnya.
Dua kegiatan bentrok bila ada sesi pada tanggal yang sama yang jamnya bertumpuk (bersentuhan tidak bentrok),
atau bila superadmin menandainya bentrok (`Kegiatan.bentrok_dengan`, misalnya Traveling dan Got Talent, R14).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from apps.inti import pengaturan
from apps.inti.models import Tingkat

from .models import Kegiatan, TingkatTitik, TitikAbsen

NAMA_HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
NAMA_BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


@dataclass(frozen=True)
class Sesi:
    tanggal: date
    mulai: time
    selesai: time
    selesai_tertulis: bool

    def bertumpuk(self, lain: Sesi) -> bool:
        return self.tanggal == lain.tanggal and self.mulai < lain.selesai and lain.mulai < self.selesai

    def teks(self) -> str:
        akhir = f"{self.selesai:%H.%M}" if self.selesai_tertulis else "selesai"
        return f"{NAMA_HARI[self.tanggal.weekday()]} {self.tanggal.day} {NAMA_BULAN[self.tanggal.month - 1]} {self.mulai:%H.%M}-{akhir}"


def _selesai_bawaan() -> time:
    teks = str(pengaturan.ambil("kegiatan.selesai_bawaan") or "12:00")
    try:
        jam, menit = teks.replace(".", ":").split(":")[:2]
        return time(int(jam), int(menit))
    except ValueError:
        return time(12, 0)


def _sesi(t: TitikAbsen, bawaan: time) -> Sesi:
    if t.selesai:
        return Sesi(t.tanggal, t.mulai, t.selesai, True)
    if bawaan > t.mulai:
        return Sesi(t.tanggal, t.mulai, bawaan, False)
    akhir = (datetime.combine(t.tanggal, t.mulai) + timedelta(hours=2)).time()
    return Sesi(t.tanggal, t.mulai, akhir if akhir > t.mulai else time(23, 59), False)


@dataclass
class PilihanKegiatan:
    kegiatan: Kegiatan
    sesi: list[Sesi]
    bentrok: set[int]

    @property
    def jadwal(self) -> str:
        return "; ".join(s.teks() for s in self.sesi)


def pilihan(tingkat: str) -> list[PilihanKegiatan]:
    """Kegiatan yang bisa dipilih untuk satu tingkat (punya sesi di tingkat itu atau Semua) + bentroknya."""
    if tingkat not in Tingkat.values:
        return []
    bawaan = _selesai_bawaan()
    per_kegiatan: dict[int, list[Sesi]] = {}
    for t in (
        TitikAbsen.objects.filter(kegiatan__bisa_dipilih=True, tingkat__in=[tingkat, TingkatTitik.SEMUA])
        .select_related("kegiatan")
        .order_by("tanggal", "mulai")
    ):
        per_kegiatan.setdefault(t.kegiatan_id, [])
        sesi = _sesi(t, bawaan)
        if sesi not in per_kegiatan[t.kegiatan_id]:
            per_kegiatan[t.kegiatan_id].append(sesi)
    daftar = [
        PilihanKegiatan(k, per_kegiatan[k.pk], set())
        for k in Kegiatan.objects.filter(pk__in=per_kegiatan, bisa_dipilih=True).order_by("urutan", "nama")
    ]
    for a in daftar:
        for b in daftar:
            if a is not b and any(x.bertumpuk(y) for x in a.sesi for y in b.sesi):
                a.bentrok.add(b.kegiatan.pk)
    # Bentrok yang ditetapkan panitia (dua arah walau hanya satu baris tersimpan).
    peta = {p.kegiatan.pk: p for p in daftar}
    for x, y in Kegiatan.bentrok_dengan.through.objects.filter(
        from_kegiatan_id__in=peta, to_kegiatan_id__in=peta
    ).values_list("from_kegiatan_id", "to_kegiatan_id"):
        if x != y:
            peta[x].bentrok.add(y)
            peta[y].bentrok.add(x)
    return daftar


def semua_tingkat() -> dict[str, list[dict]]:
    """Data untuk JavaScript form: {tingkat: [{id, nama, jadwal, bentrok: [id]}]}."""
    return {
        t: [
            {"id": p.kegiatan.pk, "nama": p.kegiatan.nama, "jadwal": p.jadwal, "bentrok": sorted(p.bentrok)}
            for p in pilihan(t)
        ]
        for t in Tingkat.values
    }


def periksa(tingkat: str, kegiatan: list[Kegiatan]) -> list[str]:
    """Pesan galat bila kegiatan tidak ada untuk tingkat itu atau jadwalnya bentrok satu sama lain."""
    tersedia = {p.kegiatan.pk: p for p in pilihan(tingkat)}
    pesan: list[str] = []
    for k in kegiatan:
        if k.pk not in tersedia:
            pesan.append(f"{k.nama} tidak tersedia untuk tingkat {Tingkat(tingkat).label}.")
    dipilih = [tersedia[k.pk] for k in kegiatan if k.pk in tersedia]
    for i, a in enumerate(dipilih):
        for b in dipilih[i + 1 :]:
            if b.kegiatan.pk in a.bentrok:
                sama = next((x for x in a.sesi for y in b.sesi if x.bertumpuk(y)), None)
                waktu = f" ({sama.teks()})" if sama else " (kegiatannya berlangsung bersamaan)"
                pesan.append(f"{a.kegiatan.nama} bentrok dengan {b.kegiatan.nama}{waktu}. Pilih salah satu.")
    return pesan


def peserta_bentrok() -> dict[int, str]:
    """Biodata aktif yang kegiatannya bentrok (misalnya memilih sebelum aturan bentrok ditambah): {pk: pesan}."""
    from apps.biodata.models import Peserta

    hasil: dict[int, str] = {}
    for tingkat in Tingkat.values:
        tersedia = {p.kegiatan.pk: p for p in pilihan(tingkat)}
        for orang in Peserta.objects.filter(tingkat=tingkat).prefetch_related("kegiatan"):
            dipilih = [tersedia[k.pk] for k in orang.kegiatan.all() if k.pk in tersedia]
            pasangan = [
                f"{a.kegiatan.nama} dan {b.kegiatan.nama}"
                for i, a in enumerate(dipilih)
                for b in dipilih[i + 1 :]
                if b.kegiatan.pk in a.bentrok
            ]
            if pasangan:
                hasil[orang.pk] = "; ".join(pasangan)
    return hasil
