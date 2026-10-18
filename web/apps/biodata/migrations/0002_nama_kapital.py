"""REVISI R3: nama lengkap dan nama orang tua/wali disimpan HURUF KAPITAL (termasuk gelar)."""

from django.db import migrations


def ke_kapital(apps, schema_editor):
    Peserta = apps.get_model("biodata", "Peserta")
    for p in Peserta.objects.all().only("id", "nama_lengkap", "nama_orang_tua"):
        baru_nama = p.nama_lengkap.replace("’", "'").upper()
        baru_ortu = p.nama_orang_tua.replace("’", "'").upper()
        if (baru_nama, baru_ortu) != (p.nama_lengkap, p.nama_orang_tua):
            Peserta.objects.filter(pk=p.pk).update(nama_lengkap=baru_nama, nama_orang_tua=baru_ortu)


class Migration(migrations.Migration):
    dependencies = [("biodata", "0001_initial")]

    # Tidak bisa dikembalikan ke huruf asli; mundur migrasi tidak mengubah apa pun.
    operations = [migrations.RunPython(ke_kapital, migrations.RunPython.noop)]
