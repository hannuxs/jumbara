"""Jadwal kegiatan revisi dari panitia (R16, 13 Nov 2026), diterapkan ke database yang sudah berisi data.

Aman untuk data produksi:
- Tidak ada yang dihapus. Titik absen diubah menurut kodenya; kehadiran yang sudah tercatat tetap menempel.
- Ranking 1 dan Ngobrol Bareng PMR pindah dari Jumat 13/11 ke Sabtu 14/11 (titik yang sama digeser), kecuali
  superadmin sudah membuat titik kegiatan itu untuk tingkat yang sama di 14/11 (titik lama dibiarkan).
- Traveling Jumat 13/11 menjadi 07.30-18.00 (sesi 07.30-11.30 dan 13.30-18.00 dicatat sekali per hari).
- Kegiatan baru Sarasehan Pengelolaan Sampah (Sabtu 14/11 08.00-12.00, per tingkat) dibuat bila belum ada.
- Database kosong (instalasi baru) dilewati: data diisi sigap_seed dari data/*.csv yang sudah diperbarui.
"""

from datetime import date, time

from django.db import migrations

JUMAT, SABTU = date(2026, 11, 13), date(2026, 11, 14)
TINGKAT = ("MULA", "MADYA", "WIRA")
GESER = {
    # kode titik: (kegiatan, tanggal baru, mulai, selesai)
    "TA-017": ("ranking-1", SABTU, time(8), None), "TA-018": ("ranking-1", SABTU, time(8), None),
    "TA-019": ("ranking-1", SABTU, time(8), None),
    "TA-026": ("ngobrol-bareng", SABTU, time(8), time(12)), "TA-027": ("ngobrol-bareng", SABTU, time(8), time(12)),
    "TA-028": ("ngobrol-bareng", SABTU, time(8), time(12)),
    "TA-023": ("traveling", JUMAT, time(7, 30), time(18)), "TA-024": ("traveling", JUMAT, time(7, 30), time(18)),
    "TA-025": ("traveling", JUMAT, time(7, 30), time(18)),
}  # fmt: skip
KODE_SAMPAH = "sarasehan-sampah"
NAMA_SAMPAH = "Sarasehan Pengelolaan Sampah"


def _kode_bebas(TitikAbsen, mulai: int) -> str:
    n = mulai
    while TitikAbsen.objects.filter(kode=f"TA-{n:03d}").exists():
        n += 1
    return f"TA-{n:03d}"


def terapkan(apps, schema_editor):
    Kegiatan = apps.get_model("absensi", "Kegiatan")
    TitikAbsen = apps.get_model("absensi", "TitikAbsen")
    if not Kegiatan.objects.filter(kode="traveling").exists():
        return  # instalasi baru: diisi sigap_seed

    for kode, (kg_kode, tanggal, mulai, selesai) in GESER.items():
        t = TitikAbsen.objects.filter(kode=kode, kegiatan__kode=kg_kode).first()
        if t is None:
            continue
        sudah_ada = (
            TitikAbsen.objects.filter(kegiatan_id=t.kegiatan_id, tingkat=t.tingkat, tanggal=tanggal)
            .exclude(pk=t.pk)
            .exists()
        )
        if sudah_ada:
            continue
        nama = t.nama_tampil.replace("Jumat", "Sabtu") if tanggal == SABTU else t.nama_tampil
        TitikAbsen.objects.filter(pk=t.pk).update(
            tanggal=tanggal, mulai=mulai, selesai=selesai, nama_tampil=nama,
            catatan=(t.catatan + " | Jadwal revisi panitia 13 Nov 2026").strip(" |"),
        )  # fmt: skip

    kg = Kegiatan.objects.filter(kode=KODE_SAMPAH).first() or Kegiatan.objects.filter(
        nama__icontains="Pengelolaan Sampah"
    ).first()
    if kg is None:
        acuan = Kegiatan.objects.filter(kode="sarasehan-pergaulan").first()
        kg = Kegiatan.objects.create(
            kode=KODE_SAMPAH, nama=NAMA_SAMPAH, kelompok="JUMPA", dipisah_per_tingkat=True, kuota_default=3,
            rincian_kuota="3 anggota PMR (disamakan dengan sarasehan lain; ubah bila panitia menentukan lain)",
            sistem_penilaian="poin tambahan", urutan=acuan.urutan if acuan else 7, bisa_dipilih=True,
            catatan="Kegiatan baru dari jadwal revisi panitia 13 Nov 2026.",
        )  # fmt: skip
    for tingkat in TINGKAT:
        if TitikAbsen.objects.filter(kegiatan=kg, tingkat=tingkat, tanggal=SABTU).exists():
            continue
        TitikAbsen.objects.create(
            kode=_kode_bebas(TitikAbsen, 61), kegiatan=kg, tingkat=tingkat, tanggal=SABTU, mulai=time(8),
            selesai=time(12), nama_tampil=f"{NAMA_SAMPAH} Sabtu {tingkat.title()}", lokasi="Tenda Utama",
            catatan="Jadwal revisi panitia 13 Nov 2026",
        )  # fmt: skip


class Migration(migrations.Migration):
    dependencies = [("absensi", "0005_daftar_ulang_tepat_waktu")]

    # Tidak dibalik otomatis: jadwal baru adalah data asli acara.
    operations = [migrations.RunPython(terapkan, migrations.RunPython.noop)]
