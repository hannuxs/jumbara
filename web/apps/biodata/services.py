"""Logika bisnis biodata: status form, simpan peserta, tanda otomatis, ubah, hapus, pulihkan."""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.inti import pengaturan
from apps.inti.log import catat, selisih
from apps.inti.pengaturan import StatusPaksa
from apps.inti.utils import ip_klien, kode_acak, user_agent
from apps.kartu import services as kartu_svc
from apps.kontingen.models import Kontingen

from . import foto as foto_mod
from . import nik as nik_mod
from .models import PERAN_DEWASA, JenisPenanda, PenandaPeserta, Peran, Peserta, Sumber

# Usia wajar peserta per tingkat (dihitung per tanggal acuan, bawaan 12 November 2026).
USIA_WAJAR = {"MULA": (8, 13), "MADYA": (11, 16), "WIRA": (14, 19)}
USIA_MIN_DEWASA = 17


class NikSudahTerdaftar(Exception):
    pass


# --- Status form --------------------------------------------------------------


@dataclass
class StatusForm:
    terbuka: bool
    alasan: str  # BUKA, BELUM_BUKA, SUDAH_TUTUP, PAKSA_TUTUP, TERKUNCI
    buka_pada: datetime | None
    tutup_pada: datetime | None


def status_form(nilai: dict | None = None, sekarang: datetime | None = None) -> StatusForm:
    """Apakah form biodata menerima kiriman saat ini. Selalu dicek di server."""
    nilai = nilai if nilai is not None else pengaturan.semua()
    sekarang = sekarang or timezone.now()
    buka = pengaturan.ke_datetime(nilai.get("biodata.buka_pada"))
    tutup = pengaturan.ke_datetime(nilai.get("biodata.tutup_pada"))
    if nilai.get("biodata.terkunci"):
        return StatusForm(False, "TERKUNCI", buka, tutup)
    paksa = nilai.get("biodata.paksa_status") or StatusPaksa.OTOMATIS
    if paksa == StatusPaksa.BUKA:
        return StatusForm(True, "BUKA", buka, tutup)
    if paksa == StatusPaksa.TUTUP:
        return StatusForm(False, "PAKSA_TUTUP", buka, tutup)
    if buka and sekarang < buka:
        return StatusForm(False, "BELUM_BUKA", buka, tutup)
    if tutup and sekarang > tutup:
        return StatusForm(False, "SUDAH_TUTUP", buka, tutup)
    return StatusForm(True, "BUKA", buka, tutup)


# --- Normalisasi --------------------------------------------------------------


def rapikan_spasi(teks: str) -> str:
    return " ".join((teks or "").split())


POLA_NAMA = re.compile(r"^[^\W\d_]+(?:[ .,'\-][^\W\d_]*)*\.?$", re.UNICODE)


def nama_valid(nama: str) -> bool:
    """Huruf, spasi, titik, koma, apostrof, tanda hubung. Tanpa angka dan simbol lain."""
    nama = nama.replace("’", "'")
    return bool(POLA_NAMA.match(nama)) and any(c.isalpha() for c in nama)


def kapital(teks: str) -> str:
    """Nama disimpan HURUF KAPITAL (termasuk gelar). Apostrof miring diseragamkan."""
    return teks.replace("’", "'").upper()


def normalisasi_telepon(teks: str) -> str | None:
    """'0812...', '+62812...', '62812...' -> '62812...'. None jika tidak valid."""
    digit = re.sub(r"[\s\-().]", "", teks or "")
    if digit.startswith("+"):
        digit = digit[1:]
    if not digit.isdigit():
        return None
    if digit.startswith("0"):
        digit = "62" + digit[1:]
    elif digit.startswith("8"):
        digit = "62" + digit
    if not digit.startswith("62") or not 10 <= len(digit) <= 15:
        return None
    return digit


def kunci_nama(nama: str) -> str:
    teks = unicodedata.normalize("NFKD", nama).encode("ascii", "ignore").decode().lower()
    # Buang gelar sesudah koma (", S.Pd") agar "Sri, S.Pd" mirip "Sri".
    teks = teks.split(",")[0]
    return re.sub(r"[^a-z]", "", teks)


def usia_pada(tanggal_lahir: date, acuan: date) -> int:
    return acuan.year - tanggal_lahir.year - ((acuan.month, acuan.day) < (tanggal_lahir.month, tanggal_lahir.day))


def tanggal_acuan_usia() -> date:
    nilai = pengaturan.ambil("acara.tanggal_acuan_usia") or "2026-11-12"
    try:
        return date.fromisoformat(nilai)
    except ValueError:
        return date(2026, 11, 12)


# --- Tanda otomatis -----------------------------------------------------------


def hitung_tanda(peserta: Peserta) -> dict[str, str]:
    """Daftar tanda {jenis: pesan} untuk satu peserta. Tidak pernah menolak kiriman."""
    tanda: dict[str, str] = {}
    kontingen = peserta.kontingen

    if peserta.tingkat != kontingen.tingkat:
        tanda[JenisPenanda.TINGKAT_BEDA] = (
            f"Memilih {peserta.get_tingkat_display()}, padahal kontingen {kontingen.get_tingkat_display()}"
        )

    sebelum = Peserta.objects.filter(kontingen=kontingen).exclude(pk=peserta.pk)
    if peserta.pk:
        sebelum = sebelum.filter(dibuat_pada__lt=peserta.dibuat_pada)
    if kontingen.kuota and sebelum.count() >= kontingen.kuota:
        tanda[JenisPenanda.KUOTA_PENUH] = f"Masuk saat kuota kontingen ({kontingen.kuota}) sudah terisi"

    usia = usia_pada(peserta.tanggal_lahir, tanggal_acuan_usia())
    if peserta.peran == Peran.PESERTA:
        rentang = USIA_WAJAR.get(peserta.tingkat)
        if rentang and not rentang[0] <= usia <= rentang[1]:
            tanda[JenisPenanda.USIA_TIDAK_WAJAR] = (
                f"Usia {usia} tahun, wajar untuk {peserta.get_tingkat_display()} {rentang[0]}-{rentang[1]} tahun"
            )
    elif peserta.peran in PERAN_DEWASA and usia < USIA_MIN_DEWASA:
        tanda[JenisPenanda.USIA_TIDAK_WAJAR] = f"Usia {usia} tahun untuk {peserta.get_peran_display()}"

    if peserta.foto_asli_hash:
        sama = Peserta.objects.filter(foto_asli_hash=peserta.foto_asli_hash).exclude(pk=peserta.pk)
        if sama.exists():
            kode = ", ".join(sama.values_list("kode_pendaftaran", flat=True)[:3])
            tanda[JenisPenanda.FOTO_DUPLIKAT] = f"Foto sama dengan {kode}"

    kunci = kunci_nama(peserta.nama_lengkap)
    if kunci:
        mirip = []
        for lain in (
            Peserta.objects.filter(kontingen=kontingen).exclude(pk=peserta.pk).only("nama_lengkap", "kode_pendaftaran")
        ):
            kunci_lain = kunci_nama(lain.nama_lengkap)
            if kunci_lain and (kunci_lain == kunci or difflib.SequenceMatcher(None, kunci, kunci_lain).ratio() >= 0.9):
                mirip.append(lain)
        if mirip:
            daftar = ", ".join(f"{p.nama_lengkap} ({p.kode_pendaftaran})" for p in mirip[:3])
            tanda[JenisPenanda.NAMA_MIRIP] = f"Mirip dengan {daftar}"[:255]
    return tanda


def terapkan_tanda(peserta: Peserta, tanda: dict[str, str]) -> None:
    """Sinkronkan tabel penanda: tambah yang baru, hapus yang sudah tidak berlaku.

    Tanda yang sudah ditandai "sudah dicek" tetap dalam status itu bila masih berlaku.
    """
    ada = {p.jenis: p for p in peserta.penanda.all()}
    for jenis, pesan in tanda.items():
        if jenis in ada:
            if ada[jenis].pesan != pesan[:255]:
                ada[jenis].pesan = pesan[:255]
                ada[jenis].save(update_fields=["pesan"])
        else:
            PenandaPeserta.objects.create(peserta=peserta, jenis=jenis, pesan=pesan[:255])
    for jenis, baris in ada.items():
        if jenis not in tanda:
            baris.delete()


def _tandai_pasangan(peserta: Peserta, tanda: dict[str, str]) -> None:
    """Nama mirip dan foto duplikat juga ditandai pada orang lainnya."""
    if JenisPenanda.NAMA_MIRIP in tanda or JenisPenanda.FOTO_DUPLIKAT in tanda:
        kunci = kunci_nama(peserta.nama_lengkap)
        for lain in Peserta.objects.filter(kontingen=peserta.kontingen).exclude(pk=peserta.pk):
            kunci_lain = kunci_nama(lain.nama_lengkap)
            if (
                kunci
                and kunci_lain
                and (kunci_lain == kunci or difflib.SequenceMatcher(None, kunci, kunci_lain).ratio() >= 0.9)
            ):
                PenandaPeserta.objects.get_or_create(
                    peserta=lain,
                    jenis=JenisPenanda.NAMA_MIRIP,
                    defaults={"pesan": f"Mirip dengan {peserta.nama_lengkap} ({peserta.kode_pendaftaran})"[:255]},
                )
        if peserta.foto_asli_hash:
            for lain in Peserta.objects.filter(foto_asli_hash=peserta.foto_asli_hash).exclude(pk=peserta.pk):
                PenandaPeserta.objects.get_or_create(
                    peserta=lain,
                    jenis=JenisPenanda.FOTO_DUPLIKAT,
                    defaults={"pesan": f"Foto sama dengan {peserta.kode_pendaftaran}"},
                )


# --- Simpan, ubah, hapus ------------------------------------------------------


def _kode_pendaftaran_baru() -> str:
    for _ in range(20):
        kode = f"SJ-{kode_acak(6)}"
        if not Peserta.semua.filter(kode_pendaftaran=kode).exists():
            return kode
    raise RuntimeError("Gagal membuat kode pendaftaran unik")


def nik_terdaftar(nik: str, kecuali_pk: int | None = None) -> bool:
    qs = Peserta.objects.filter(nik_hash=nik_mod.hash_nik(nik))
    if kecuali_pk:
        qs = qs.exclude(pk=kecuali_pk)
    return qs.exists()


def _isi_dari_data(peserta: Peserta, data: dict) -> None:
    peserta.kontingen = data["kontingen"]
    peserta.tingkat = data["tingkat"]
    peserta.peran = data["peran"]
    peserta.nama_lengkap = data["nama_lengkap"]
    peserta.nomor_induk_anggota = data.get("nomor_induk_anggota", "")
    peserta.jenis_kelamin = data["jenis_kelamin"]
    peserta.tempat_lahir = data["tempat_lahir"]
    peserta.tanggal_lahir = data["tanggal_lahir"]
    peserta.alamat = data["alamat"]
    peserta.golongan_darah = data["golongan_darah"]
    peserta.telepon = data.get("telepon", "")
    peserta.nama_orang_tua = data.get("nama_orang_tua", "")
    peserta.telepon_orang_tua = data.get("telepon_orang_tua", "")
    nik = data["nik"]
    peserta.nik_terenkripsi = nik_mod.enkripsi(nik)
    peserta.nik_hash = nik_mod.hash_nik(nik)
    peserta.nik_samar = nik_mod.samarkan(nik)
    peserta.nik_akhir4 = nik[-4:]


def ringkasan_log(peserta: Peserta) -> dict:
    """Data peserta untuk log (NIK disamarkan, tanpa alamat lengkap dan foto)."""
    return {
        "kode_pendaftaran": peserta.kode_pendaftaran,
        "kontingen": peserta.kontingen.kode if peserta.kontingen_id else None,
        "tingkat": peserta.tingkat,
        "peran": peserta.peran,
        "nama_lengkap": peserta.nama_lengkap,
        "nik": peserta.nik_samar,
        "nomor_induk_anggota": peserta.nomor_induk_anggota,
        "jenis_kelamin": peserta.jenis_kelamin,
        "tempat_lahir": peserta.tempat_lahir,
        "tanggal_lahir": peserta.tanggal_lahir.isoformat() if peserta.tanggal_lahir else None,
        "alamat": "(diubah)" if peserta.alamat else "",
        "golongan_darah": peserta.golongan_darah,
        "telepon": peserta.telepon[:-4] + "****" if peserta.telepon else "",
        "nama_orang_tua": peserta.nama_orang_tua,
        "telepon_orang_tua": peserta.telepon_orang_tua[:-4] + "****" if peserta.telepon_orang_tua else "",
        "foto": "ada" if peserta.foto_path else "tidak ada",
    }


def buat_peserta(request, data: dict, hasil_foto: foto_mod.HasilFoto | None, sumber: str) -> Peserta:
    """Simpan biodata baru + foto + tanda. Melempar NikSudahTerdaftar bila NIK dobel."""
    peserta = Peserta(sumber=sumber)
    _isi_dari_data(peserta, data)
    peserta.kode_pendaftaran = _kode_pendaftaran_baru()
    # Token QR kartu dibuat saat biodata masuk (Tahap 2). Bila data sudah dikunci untuk cetak,
    # biodata baru (tambahan superadmin) langsung ditandai perlu dicetak.
    kartu_svc.pasang_token(peserta)
    peserta.perlu_cetak_ulang = kartu_svc.data_terkunci()
    peserta.persetujuan_data_pada = timezone.now() if data.get("persetujuan") else None
    peserta.ip_pengirim = ip_klien(request)
    peserta.user_agent_pengirim = user_agent(request)

    path_foto = ""
    if hasil_foto:
        path_foto = foto_mod.simpan(peserta.kode_pendaftaran, hasil_foto.isi_jpeg, timezone.localdate().year)
        peserta.foto_path = path_foto
        peserta.foto_asli_hash = hasil_foto.hash_asli
    try:
        with transaction.atomic():
            peserta.save()
            tanda = hitung_tanda(peserta)
            terapkan_tanda(peserta, tanda)
            _tandai_pasangan(peserta, tanda)
            aksi = "biodata.dibuat" if sumber == Sumber.FORM_PUBLIK else "biodata.ditambah_superadmin"
            catat(request, aksi, peserta, keterangan=peserta.kode_pendaftaran, baru=ringkasan_log(peserta))
    except IntegrityError as e:
        if path_foto:
            foto_mod.hapus(path_foto)
        if "nik" in str(e).lower():
            raise NikSudahTerdaftar from e
        raise
    return peserta


def ubah_peserta(request, peserta: Peserta, data: dict, hasil_foto: foto_mod.HasilFoto | None) -> Peserta:
    """Superadmin memperbaiki biodata. Riwayat perubahan dicatat di log."""
    lama = ringkasan_log(peserta)
    tercetak_lama = kartu_svc.potret_isian_tercetak(peserta)
    nik_lama = nik_mod.dekripsi(peserta.nik_terenkripsi)
    _isi_dari_data(peserta, data)
    foto_lama = ""
    if hasil_foto:
        foto_lama = peserta.foto_path
        # Nama file baru agar foto lama tetap ada sampai transaksi berhasil.
        nama = f"{peserta.kode_pendaftaran}-{kode_acak(4)}"
        peserta.foto_path = foto_mod.simpan(nama, hasil_foto.isi_jpeg, timezone.localdate().year)
        peserta.foto_asli_hash = hasil_foto.hash_asli
    # Setelah data dikunci, perubahan isian yang tercetak di kartu menandai kartu perlu dicetak ulang.
    cetak_ulang = kartu_svc.perlu_cetak_ulang_karena_ubah(tercetak_lama, peserta)
    if cetak_ulang:
        peserta.perlu_cetak_ulang = True
    try:
        with transaction.atomic():
            peserta.save()
            tanda = hitung_tanda(peserta)
            terapkan_tanda(peserta, tanda)
            _tandai_pasangan(peserta, tanda)
            baru = ringkasan_log(peserta)
            if cetak_ulang:
                baru["kartu"] = "perlu dicetak ulang (data sudah dikunci)"
            if nik_lama != data["nik"]:
                baru["nik"] = f"{peserta.nik_samar} (NIK diganti)"
            if hasil_foto:
                baru["foto"] = "diganti"
            d_lama, d_baru = selisih(lama, baru)
            catat(request, "biodata.diubah", peserta, keterangan=peserta.kode_pendaftaran, lama=d_lama, baru=d_baru)
    except IntegrityError as e:
        if hasil_foto:
            foto_mod.hapus(peserta.foto_path)
        if "nik" in str(e).lower():
            raise NikSudahTerdaftar from e
        raise
    if foto_lama and foto_lama != peserta.foto_path:
        foto_mod.hapus(foto_lama)
    return peserta


def hapus_peserta(request, peserta: Peserta) -> None:
    with transaction.atomic():
        peserta.hapus_lunak(oleh=getattr(request, "nama_pelaku", "") or request.user.username)
        catat(request, "biodata.dihapus", peserta, keterangan=f"{peserta.kode_pendaftaran} ke tempat sampah")


def pulihkan_peserta(request, peserta: Peserta) -> None:
    """Kembalikan dari tempat sampah. Ditolak jika NIK-nya sudah dipakai biodata aktif lain."""
    if Peserta.objects.filter(nik_hash=peserta.nik_hash).exclude(pk=peserta.pk).exists():
        raise NikSudahTerdaftar
    try:
        with transaction.atomic():
            peserta.pulihkan()
            catat(request, "biodata.dipulihkan", peserta, keterangan=peserta.kode_pendaftaran)
    except IntegrityError as e:
        raise NikSudahTerdaftar from e


def hapus_permanen_peserta(request, peserta: Peserta) -> None:
    kode = peserta.kode_pendaftaran
    path = peserta.foto_path
    ringkas = ringkasan_log(peserta)
    with transaction.atomic():
        catat(request, "biodata.dihapus_permanen", peserta, keterangan=kode, lama=ringkas)
        peserta.delete()
    foto_mod.hapus(path)


def abaikan_tanda(request, tanda: PenandaPeserta) -> None:
    tanda.diabaikan_oleh = (getattr(request, "nama_pelaku", "") or request.user.username)[:100]
    tanda.diabaikan_pada = timezone.now()
    tanda.save(update_fields=["diabaikan_oleh", "diabaikan_pada"])
    catat(request, "tanda.dicek", tanda.peserta, keterangan=f"{tanda.get_jenis_display()} ditandai sudah dicek")


def hitung_ulang_tanda_kontingen(kontingen: Kontingen) -> None:
    """Dipanggil saat kuota kontingen berubah: perbarui tanda KUOTA_PENUH semua anggotanya."""
    anggota = list(Peserta.objects.filter(kontingen=kontingen).order_by("dibuat_pada", "id"))
    for urutan, peserta in enumerate(anggota):
        penuh = kontingen.kuota and urutan >= kontingen.kuota
        qs = PenandaPeserta.objects.filter(peserta=peserta, jenis=JenisPenanda.KUOTA_PENUH)
        if penuh and not qs.exists():
            PenandaPeserta.objects.create(
                peserta=peserta,
                jenis=JenisPenanda.KUOTA_PENUH,
                pesan=f"Masuk saat kuota kontingen ({kontingen.kuota}) sudah terisi",
            )
        elif not penuh:
            qs.delete()
