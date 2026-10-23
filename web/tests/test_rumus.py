"""Tes unit mesin rumus (docs/16-FORM-BUILDER.md): tanpa eval, tokenizer, prioritas, fungsi, galat."""

from __future__ import annotations

import pytest

from apps.penilaian import rumus as r


def h(teks: str, nilai: dict | None = None, ref=None, peringkat=None):
    nilai = nilai or {}
    k = r.Konteks(
        nilai=lambda kode: nilai.get(kode),
        ref=ref or (lambda slug, kode, ti: None),
        peringkat=peringkat or (lambda kode, naik: None),
    )
    return r.hitung_aman(r.urai(teks), k, "uji"), k


@pytest.mark.parametrize(
    "teks,hasil",
    [
        ("1 + 2 * 3", 7),
        ("(1 + 2) * 3", 9),
        ("10 - 4 - 3", 3),
        ("12 / 3 / 2", 2),
        ("-2 * 3", -6),
        ("2 * -3", -6),
        ("--2", 2),
        ("0,25 * 8", 2),
        ("0.25*8", 2),
        (".5 + .5", 1),
        ("3 x 4", 12),
        ("3 X 4", 12),
        ("3 × 4", 12),
        ("8 : 2", 4),
        ("2 > 1", 1),
        ("2 <= 1", 0),
        ("2 = 2", 1),
        ("2 <> 2", 0),
        ("2 != 3", 1),
        ("1 + 2 = 3", 1),
    ],
)
def test_operator_dan_prioritas(teks, hasil):
    assert h(teks)[0] == pytest.approx(hasil)


def test_kolom_dan_rumus_template():
    nilai = {"pengetahuan": 80, "sikap": 90, "keterampilan": 70, "poin_kehadiran": 6}
    v, _ = h("0.25*[pengetahuan] + 0.25*[sikap] + 0.5*[keterampilan] + [poin_kehadiran]", nilai)
    assert v == pytest.approx(0.25 * 80 + 0.25 * 90 + 0.5 * 70 + 6)
    assert h("[Pengetahuan] + 1", nilai)[0] == 81  # kode kolom tidak peka huruf besar


@pytest.mark.parametrize(
    "teks,hasil",
    [
        ("SUM(1, 2, 3)", 6),
        ("SUM(1;2;3)", 6),
        ("AVG(2, 4)", 3),
        ("RATA(2, 4)", 3),
        ("MIN(5, 2, 9)", 2),
        ("MAX(5, 2, 9)", 9),
        ("ABS(-3)", 3),
        ("ROUND(2.345, 2)", 2.35),
        ("ROUND(2.5)", 3),
        ("ROUND(-2.5)", -3),
        ("IF(1 > 2, 10, 20)", 20),
        ("JIKA(3 > 2, 10, 20)", 10),
        ("AND(1, 1, 0)", 0),
        ("OR(0, 0, 1)", 1),
        ("NOT(0)", 1),
        ("POIN_PERINGKAT(1, 10, 8, 6, 4, 2)", 10),
        ("POIN_PERINGKAT(3, 10, 8, 6, 4, 2)", 6),
        ("POIN_PERINGKAT(6, 10, 8, 6, 4, 2)", 0),
        ("POIN_PERINGKAT(0, 10, 8)", 0),
        ("POIN_PERINGKAT(1.5, 10, 8)", 0),
        ("sum(1, 2)", 3),
    ],
)
def test_fungsi(teks, hasil):
    assert h(teks)[0] == pytest.approx(hasil)


def test_nilai_kosong():
    kosong = {"a": None, "b": 4}
    assert h("[a] + [b]", kosong)[0] == 4  # kosong dianggap 0 dalam hitungan
    assert h("SUM([a], [b])", kosong)[0] == 4
    assert h("AVG([a], [b])", kosong)[0] == 4  # AVG mengabaikan yang kosong
    assert h("AVG([a])", kosong)[0] is None
    assert h("MAX([a])", kosong)[0] is None
    assert h("ISBLANK([a])", kosong)[0] == 1
    assert h("ISBLANK([b])", kosong)[0] == 0
    assert h("COALESCE([a], 7)", kosong)[0] == 7
    assert h("COALESCE([b], 7)", kosong)[0] == 4
    assert h("[a]", kosong)[0] is None
    assert h("-[a]", kosong)[0] is None
    assert h("POIN_PERINGKAT([a], 10, 8)", kosong)[0] == 0


def test_bagi_nol_kosong_dengan_peringatan():
    v, k = h("[a] / [b]", {"a": 5, "b": 0})
    assert v is None and "Pembagian dengan nol" in k.peringatan[0]
    assert h("IF([b] = 0, 0, [a] / [b])", {"a": 5, "b": 0})[0] == 0  # IF hanya menghitung cabang terpilih


def test_ref_dan_peringkat_lewat_konteks():
    panggilan = []

    def ref(slug, kode, tingkat_ini):
        panggilan.append((slug, kode, tingkat_ini))
        return 2.0

    v, _ = h('POIN_PERINGKAT(REF("ranking-1", "peringkat"), 10, 8, 6)', ref=ref)
    assert v == 8 and panggilan == [("ranking-1", "peringkat", False)]
    h('REF("penilaian-traveling", "Nilai_Akhir", "TINGKAT_INI")', ref=ref)
    assert panggilan[-1] == ("penilaian-traveling", "nilai_akhir", True)
    v, _ = h(
        'PERINGKAT([nilai], "NAIK")', peringkat=lambda kode, naik: 3.0 if (kode, naik) == ("nilai", True) else None
    )
    assert v == 3


@pytest.mark.parametrize(
    "teks,potongan",
    [
        ("", "kosong"),
        ("   ", "kosong"),
        ("1 +", "berakhir terlalu cepat"),
        ("(1 + 2", "belum ditutup"),
        ("1 + 2)", "tidak berpasangan"),
        ("[nilai", "belum ditutup"),
        ("[Nilai Akhir]", "tidak valid"),
        ("nilai + 1", "Kolom ditulis dalam kurung siku"),
        ("FOO(1)", "tidak dikenal"),
        ("ROUND(1, 2, 3)", "butuh 1 sampai 2 argumen"),
        ("IF(1, 2)", "butuh 3 argumen"),
        ("SUM()", "minimal 1"),
        ("REF(slug, kolom)", "tanda kutip"),
        ('REF("a", "b", "LAIN")', "TINGKAT_INI"),
        ("PERINGKAT(1)", "butuh kolom"),
        ('SUM("teks")', "Teks dalam kutip"),
        ('"teks"', "hanya berisi teks"),
        ("1 2", "Ada yang kurang"),
        ("1, 2", "Koma di luar fungsi"),
        ("MAX(1,2)", "membingungkan"),
        ("POIN_PERINGKAT([p], 10,8,6)", "membingungkan"),
        ("1 < 2 < 3", "berantai"),
        ("1 $ 2", "tidak dikenal"),
        ("2 ! 3", "Tanda !"),
        ("__import__('os')", "tidak dikenal"),
        ("[a].__class__", "tidak dikenal"),
        ("(" * 100 + "1" + ")" * 100, "bertingkat"),
        ("1" + "+1" * 1500, "terlalu panjang"),
    ],
)
def test_galat_penulisan(teks, potongan):
    with pytest.raises(r.GalatRumus) as e:
        r.urai(teks)
    assert potongan in str(e.value)


def test_tidak_ada_eval_atau_akses_python():
    # Teks berbahaya diperlakukan sebagai kata tak dikenal; mesin tidak pernah menjalankan kode Python.
    for jahat in ["__import__('os').system('dir')", "open('x')", "lambda: 1", "[x for x in y]", "1; import os"]:
        with pytest.raises(r.GalatRumus):
            r.urai(jahat)
    sumber = open(r.__file__, encoding="utf-8").read()
    assert "eval(" not in sumber.replace("# ", "") and "exec(" not in sumber


def test_rujukan_dan_urutan_hitung():
    s = r.urai('[a] + PERINGKAT([b]) + REF("form-x", "nilai") + REF("form-y", "p", "TINGKAT_INI")')
    ruj = r.rujukan(s)
    assert ruj.kolom == {"a", "b"}
    assert ruj.ref == [("form-x", "nilai", False), ("form-y", "p", True)]
    urut = r.urutan_hitung({"c": {"a", "b"}, "d": {"c"}, "e": {"d", "c"}})
    assert urut.index("c") < urut.index("d") < urut.index("e")


def test_rumus_melingkar_ditolak():
    with pytest.raises(r.GalatRumus) as e:
        r.urutan_hitung({"a": {"b"}, "b": {"c"}, "c": {"a"}})
    assert "melingkar" in str(e.value) and "[a]" in str(e.value)
    with pytest.raises(r.GalatRumus):
        r.urutan_hitung({"a": {"a"}})


def test_presisi_penuh_dan_angka_besar():
    v, _ = h("1 / 3 * 3")
    assert v == pytest.approx(1.0)
    v, k = h("10 * 10 * 10 * 10 * 10 * 10 * 10 * 10 * 10 * 10 * 10 * 10 * 10 * 10 * 10 * 10 * 10 * 10 * 10 * 10")
    assert v == pytest.approx(1e20)
