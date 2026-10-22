"""Tahap 2: isi token QR untuk biodata dan kontingen yang dibuat sebelum fitur kartu ada."""

import secrets

from django.db import migrations

ALFABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def _acak():
    return "".join(secrets.choice(ALFABET) for _ in range(26))


def isi_token(apps, schema_editor):
    Peserta = apps.get_model("biodata", "Peserta")
    Kontingen = apps.get_model("kontingen", "Kontingen")
    from django.utils import timezone

    dipakai = set(Peserta.objects.exclude(qr_token=None).values_list("qr_token", flat=True))
    kode_dipakai = {t[:4] + "-" + t[4:8] for t in dipakai}
    for p in Peserta.objects.filter(qr_token=None):
        while True:
            t = _acak()
            kode = t[:4] + "-" + t[4:8]
            if t not in dipakai and kode not in kode_dipakai:
                break
        dipakai.add(t)
        kode_dipakai.add(kode)
        Peserta.objects.filter(pk=p.pk).update(qr_token=t, kode_kartu=kode)
    dipakai_k = set(Kontingen.objects.exclude(qr_token=None).values_list("qr_token", flat=True))
    for k in Kontingen.objects.filter(qr_token=None):
        t = _acak()
        while t in dipakai_k:
            t = _acak()
        dipakai_k.add(t)
        Kontingen.objects.filter(pk=k.pk).update(qr_token=t, qr_token_dibuat_pada=timezone.now())


class Migration(migrations.Migration):
    dependencies = [
        ("kartu", "0001_initial"),
        ("biodata", "0003_hapus_tanda_nik"),
        ("kontingen", "0001_initial"),
    ]

    operations = [migrations.RunPython(isi_token, migrations.RunPython.noop)]
