"""Tes alamat file statis berversi (mencegah CSS/JS lama dari cache browser, REVISI R1c)."""

import re

from apps.inti.templatetags.sigap import aset


def test_aset_berversi_saat_pengembangan(settings):
    settings.DEBUG = True
    assert re.fullmatch(r"/static/js/biodata\.js\?v=\d+", aset("js/biodata.js"))


def test_halaman_form_memakai_aset_berversi(client, settings):
    settings.DEBUG = True
    isi = client.get("/daftar/").content.decode()
    for nama in ("css/app.css", "js/biodata.js", "js/sigap.js", "vendor/alpine-3.14.9.min.js"):
        assert re.search(rf"/static/{re.escape(nama)}\?v=\d+", isi), nama
