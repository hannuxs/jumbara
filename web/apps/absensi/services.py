"""Inti absensi: status titik absen, pindai idempoten yang aman untuk banyak HP bersamaan.

Kebersamaan (docs/02-ARSITEKTUR.md):
- UNIQUE (titik_absen, peserta, aktif_key) di database mencegah kehadiran ganda; tidak ada pola
  "cek dulu lalu simpan" tanpa kunci unik.
- `client_uuid` UNIQUE: kiriman ulang dari antrean offline mengembalikan jawaban yang sama.
- Transaksi pendek: baca kartu, cek titik, sisipkan satu baris.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.biodata.models import Peserta
from apps.inti import pengaturan
from apps.inti.log import catat
from apps.kartu.services import kenali

from .models import Kehadiran, Metode, PindaianDitolak, StatusTitik, TingkatTitik, TitikAbsen

HIJAU, KUNING, MERAH = "HIJAU", "KUNING", "MERAH"


# --- Status titik absen ----------------------------------------------------------


def jendela_titik(titik: TitikAbsen, nilai: dict | None = None) -> tuple[datetime, datetime]:
    """Rentang waktu titik bisa dipindai saat status OTOMATIS.

    Bawaan: 60 menit sebelum mulai sampai 60 menit setelah selesai; bila selesai kosong, sampai 23.59.
    """
    nilai = nilai if nilai is not None else pengaturan.semua()
    sebelum = int(nilai.get("absensi.menit_sebelum", 60) or 0)
    sesudah = int(nilai.get("absensi.menit_sesudah", 60) or 0)
    tz = timezone.get_current_timezone()
    mulai = timezone.make_aware(datetime.combine(titik.tanggal, titik.mulai), tz) - timedelta(minutes=sebelum)
    if titik.selesai:
        akhir = timezone.make_aware(datetime.combine(titik.tanggal, titik.selesai), tz) + timedelta(minutes=sesudah)
    else:
        akhir = timezone.make_aware(datetime.combine(titik.tanggal, time(23, 59, 59)), tz)
    return mulai, akhir


def titik_terbuka(titik: TitikAbsen, pada: datetime | None = None, nilai: dict | None = None) -> bool:
    if titik.status == StatusTitik.BUKA:
        return True
    if titik.status == StatusTitik.TUTUP:
        return False
    pada = pada or timezone.now()
    mulai, akhir = jendela_titik(titik, nilai)
    return mulai <= pada <= akhir


def kelompok_titik(titik: TitikAbsen, sekarang: datetime | None = None, nilai: dict | None = None) -> str:
    """BERLANGSUNG, NANTI_HARI_INI, SUDAH_LEWAT (hari ini), HARI_LAIN, atau TUTUP."""
    sekarang = sekarang or timezone.now()
    if titik.status == StatusTitik.TUTUP:
        return "TUTUP"
    if titik_terbuka(titik, sekarang, nilai):
        return "BERLANGSUNG"
    if titik.tanggal == timezone.localdate(sekarang):
        mulai, _ = jendela_titik(titik, nilai)
        return "NANTI_HARI_INI" if sekarang < mulai else "SUDAH_LEWAT"
    return "HARI_LAIN"


# --- Pindai ------------------------------------------------------------------------


@dataclass
class HasilPindai:
    status: str
    kode: str
    pesan: str
    peserta: dict | None = None
    tercatat_pada: str = ""
    oleh: str = ""
    info_bentrok: str = ""
    extra: dict = field(default_factory=dict)

    def json(self) -> dict:
        data = {
            "status": self.status,
            "kode": self.kode,
            "pesan": self.pesan,
            "peserta": self.peserta,
            "tercatat_pada": self.tercatat_pada,
            "oleh": self.oleh,
            "info_bentrok": self.info_bentrok,
        }
        data.update(self.extra)
        return data


def data_peserta(p: Peserta) -> dict:
    """Hanya data yang boleh dilihat panitia: nama, kontingen, tingkat, peran."""
    return {
        "id": p.pk,
        "nama": p.nama_lengkap,
        "kontingen": p.kontingen.nama,
        "kode_kontingen": p.kontingen.kode,
        "tingkat": p.tingkat,
        "peran": p.get_peran_display(),
    }


def _jam(dt: datetime) -> str:
    return f"{timezone.localtime(dt):%H.%M}"


class DataTidakValid(ValueError):
    pass


@dataclass
class Permintaan:
    client_uuid: uuid.UUID
    titik_absen_id: int
    qr: str
    dipindai_pada: datetime
    nama_pemindai: str
    perangkat_id: str
    metode: str
    offline: bool
    peserta_id: int | None = None
    alasan: str = ""


def baca_permintaan(data: dict) -> Permintaan:
    """Validasi data dari HP (jangan percaya browser)."""
    if not isinstance(data, dict):
        raise DataTidakValid("Format data salah.")
    try:
        cu = uuid.UUID(str(data.get("client_uuid", "")))
    except ValueError:
        raise DataTidakValid("client_uuid tidak valid.") from None
    try:
        titik_id = int(data.get("titik_absen_id"))
    except (TypeError, ValueError):
        raise DataTidakValid("Titik absen tidak valid.") from None
    nama = " ".join(str(data.get("nama_pemindai", "")).split())[:100]
    if not nama:
        raise DataTidakValid("Nama pemindai wajib diisi.")
    metode = data.get("metode") or Metode.SCAN
    if metode not in Metode.values:
        raise DataTidakValid("Metode tidak valid.")
    sekarang = timezone.now()
    pada = parse_datetime(str(data.get("dipindai_pada") or "")) if data.get("dipindai_pada") else None
    if pada is None:
        pada = sekarang
    elif timezone.is_naive(pada):
        pada = timezone.make_aware(pada)
    # Jam HP yang terlalu jauh dari jam server tidak dipercaya.
    if pada > sekarang + timedelta(minutes=10) or pada < sekarang - timedelta(days=2):
        pada = sekarang
    peserta_id = None
    if metode == Metode.MANUAL:
        try:
            peserta_id = int(data.get("peserta_id"))
        except (TypeError, ValueError):
            raise DataTidakValid("Pilih orang untuk absen manual.") from None
    return Permintaan(
        client_uuid=cu,
        titik_absen_id=titik_id,
        qr=str(data.get("qr", ""))[:120],
        dipindai_pada=pada,
        nama_pemindai=nama,
        perangkat_id=str(data.get("perangkat_id", ""))[:64],
        metode=metode,
        offline=bool(data.get("offline")),
        peserta_id=peserta_id,
        alasan=str(data.get("alasan", ""))[:255],
    )


def _tolak(
    req: Permintaan, titik: TitikAbsen | None, kode: str, pesan: str, peserta: Peserta | None = None
) -> HasilPindai:
    try:
        with transaction.atomic():
            PindaianDitolak.objects.create(
                titik_absen=titik,
                peserta=peserta,
                kode=kode,
                qr_ringkas=req.qr[:12] + ("..." if len(req.qr) > 12 else ""),
                client_uuid=req.client_uuid,
                nama_pemindai=req.nama_pemindai,
                perangkat_id=req.perangkat_id,
            )
    except IntegrityError:
        pass  # kiriman ulang dari antrean: sudah tercatat
    return HasilPindai(MERAH, kode, pesan, peserta=data_peserta(peserta) if peserta else None)


def _info_bentrok(kehadiran: Kehadiran) -> str:
    """Info kuning kecil bila orang yang sama juga tercatat di titik lain yang waktunya bertabrakan."""
    titik = kehadiran.titik_absen
    lain = (
        Kehadiran.objects.filter(peserta_id=kehadiran.peserta_id, titik_absen__tanggal=titik.tanggal)
        .exclude(titik_absen_id=titik.pk)
        .select_related("titik_absen")
    )
    a1 = titik.mulai
    b1 = titik.selesai or time(23, 59)
    for k in lain:
        t = k.titik_absen
        if t.mulai < b1 and a1 < (t.selesai or time(23, 59)):
            return f"Juga tercatat di {t.nama_tampil} pukul {_jam(k.diterima_pada)}"
    return ""


def _hasil_dari_kehadiran(k: Kehadiran, status: str, kode: str, pesan: str) -> HasilPindai:
    return HasilPindai(
        status,
        kode,
        pesan,
        peserta=data_peserta(k.peserta),
        tercatat_pada=_jam(k.diterima_pada),
        oleh=k.nama_pemindai,
        info_bentrok=_info_bentrok(k),
    )


def jawaban_ulang(client_uuid: uuid.UUID) -> HasilPindai | None:
    """Kiriman dengan client_uuid yang sudah pernah diproses: kembalikan jawaban yang sama."""
    k = Kehadiran.semua.filter(client_uuid=client_uuid).select_related("peserta__kontingen", "titik_absen").first()
    if k is not None:
        return _hasil_dari_kehadiran(k, HIJAU, "BERHASIL", "Berhasil")
    d = PindaianDitolak.objects.filter(client_uuid=client_uuid).select_related("peserta__kontingen").first()
    if d is not None:
        return HasilPindai(
            MERAH, d.kode, PESAN_MERAH.get(d.kode, "Ditolak"), peserta=data_peserta(d.peserta) if d.peserta else None
        )
    return None


PESAN_MERAH = {
    "TITIK_TIDAK_ADA": "Titik absen tidak ditemukan.",
    "TITIK_TUTUP": "Titik absen ini sedang tertutup.",
    "KARTU_TIDAK_DIKENAL": "Kartu tidak dikenal.",
    "KARTU_NONAKTIF": "Kartu sudah dinonaktifkan. Gunakan kartu terbaru.",
    "BUKAN_KARTU_PESERTA": "Ini QR kontingen, bukan kartu peserta.",
    "QR_ASING": "Ini bukan kartu SIGAP JUMBARA.",
    "TINGKAT_BEDA": "Tingkat tidak sesuai.",
    "PESERTA_TIDAK_ADA": "Orang tidak ditemukan.",
}


def pindai(user, data: dict, izinkan_tingkat_beda: bool = False) -> HasilPindai:
    """Proses satu pindaian (atau absen manual). Aman dipanggil bersamaan dari banyak HP."""
    req = baca_permintaan(data)
    ulang = jawaban_ulang(req.client_uuid)
    if ulang is not None:
        return ulang

    titik = TitikAbsen.objects.select_related("kegiatan").filter(pk=req.titik_absen_id).first()
    if titik is None:
        return _tolak(req, None, "TITIK_TIDAK_ADA", PESAN_MERAH["TITIK_TIDAK_ADA"])

    superadmin = getattr(user, "superadmin", False)
    if not superadmin:
        terbuka = titik_terbuka(titik)
        # Pindaian dari antrean offline dinilai menurut jam saat dipindai di HP.
        if not terbuka and req.offline:
            terbuka = titik_terbuka(titik, req.dipindai_pada)
        if not terbuka:
            return _tolak(req, titik, "TITIK_TUTUP", f"Titik absen {titik.nama_tampil} sedang tertutup.")

    if req.metode == Metode.MANUAL:
        peserta = Peserta.objects.select_related("kontingen").filter(pk=req.peserta_id).first()
        if peserta is None:
            return _tolak(req, titik, "PESERTA_TIDAK_ADA", PESAN_MERAH["PESERTA_TIDAK_ADA"])
        if not peserta.kartu_aktif and not superadmin:
            return _tolak(req, titik, "KARTU_NONAKTIF", "Kartu orang ini dinonaktifkan. Hubungi superadmin.", peserta)
    else:
        hasil = kenali(req.qr)
        if hasil.kode != "BERHASIL":
            return _tolak(req, titik, hasil.kode, hasil.pesan, hasil.peserta)
        peserta = hasil.peserta

    if titik.tingkat != TingkatTitik.SEMUA and peserta.tingkat != titik.tingkat and not izinkan_tingkat_beda:
        pesan = (
            f"Tingkat tidak sesuai: kartu ini {peserta.get_tingkat_display()}, "
            f"titik absen ini {titik.get_tingkat_display()}."
        )
        return _tolak(req, titik, "TINGKAT_BEDA", pesan, peserta)

    try:
        with transaction.atomic():
            k = Kehadiran.objects.create(
                titik_absen=titik,
                peserta=peserta,
                dipindai_pada=req.dipindai_pada,
                nama_pemindai=req.nama_pemindai,
                perangkat_id=req.perangkat_id,
                metode=req.metode,
                client_uuid=req.client_uuid,
                offline=req.offline,
                alasan_manual=req.alasan if req.metode == Metode.MANUAL else "",
            )
    except IntegrityError:
        ulang = jawaban_ulang(req.client_uuid)  # kiriman sama yang masuk bersamaan
        if ulang is not None:
            return ulang
        ada = (
            Kehadiran.objects.select_related("peserta__kontingen", "titik_absen")
            .filter(titik_absen=titik, peserta=peserta)
            .first()
        )
        if ada is None:  # sangat jarang: baris lain baru saja dibatalkan
            raise
        return _hasil_dari_kehadiran(
            ada, KUNING, "SUDAH_TERCATAT", f"Sudah tercatat pukul {_jam(ada.diterima_pada)} oleh {ada.nama_pemindai}"
        )
    k.peserta = peserta
    k.titik_absen = titik
    return _hasil_dari_kehadiran(k, HIJAU, "BERHASIL", "Berhasil")


# --- Pengelolaan oleh superadmin -----------------------------------------------------


def batalkan_kehadiran(request, kehadiran: Kehadiran) -> None:
    oleh = getattr(request, "nama_pelaku", "") or request.user.username
    with transaction.atomic():
        kehadiran.hapus_lunak(oleh=oleh)
        catat(
            request,
            "kehadiran.dibatalkan",
            kehadiran,
            keterangan=f"{kehadiran.peserta.nama_lengkap} di {kehadiran.titik_absen.kode} dibatalkan",
        )


def tambah_manual(request, titik: TitikAbsen, peserta: Peserta, alasan: str, izinkan_tingkat_beda: bool) -> HasilPindai:
    data = {
        "client_uuid": str(uuid.uuid4()),
        "titik_absen_id": titik.pk,
        "metode": Metode.MANUAL,
        "peserta_id": peserta.pk,
        "nama_pemindai": getattr(request, "nama_pelaku", "") or request.user.username,
        "perangkat_id": getattr(request, "perangkat_id", ""),
        "alasan": alasan,
    }
    hasil = pindai(request.user, data, izinkan_tingkat_beda=izinkan_tingkat_beda)
    if hasil.status == HIJAU:
        catat(request, "kehadiran.ditambah_manual", peserta, keterangan=f"{titik.kode}: {alasan}"[:255])
    return hasil
