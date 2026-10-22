"""Tes perintah sigap_uji_beban terhadap server sungguhan (live_server) dalam ukuran kecil."""

from __future__ import annotations

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.absensi.models import Kehadiran, TitikAbsen
from apps.akun.models import Pengguna
from apps.biodata.models import Peserta
from apps.kontingen.models import Kontingen


@pytest.mark.django_db(transaction=True)
def test_uji_beban_kecil_lulus_dan_bersih(live_server, panitia, superadmin, capsys):
    sandi_lama = Pengguna.objects.get(pk=panitia.pk).password
    call_command("sigap_uji_beban", url=live_server.url, perangkat=4, titik=2, pindaian=6, jeda=0.0, ya=True)
    keluar = capsys.readouterr().out
    assert "Uji beban LULUS." in keluar and "0 pasangan (titik, peserta) ganda" in keluar
    # Hanya data buatannya sendiri yang dihapus; akun panitia tetap ada dan sandinya tidak berubah.
    assert Pengguna.objects.filter(pk=panitia.pk, password=sandi_lama).exists()
    assert Pengguna.objects.filter(pk=superadmin.pk).exists()
    assert not Kontingen.semua.filter(kode="UJI-BEBAN").exists()
    assert not TitikAbsen.objects.filter(kode__startswith="UB-").exists()
    assert not Peserta.semua.exists() and not Kehadiran.semua.exists()


def test_uji_beban_butuh_ya_dan_url_benar(panitia, settings):
    settings.DEBUG = False
    with pytest.raises(CommandError, match="--ya"):
        call_command("sigap_uji_beban", url="http://127.0.0.1:1")
    with pytest.raises(CommandError, match="http"):
        call_command("sigap_uji_beban", url="file:///c:/", ya=True)
