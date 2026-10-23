/* Editor tata letak piagam: seret kotak teks di pratinjau (posisi dalam mm), ubah isian, simpan. */
document.addEventListener("alpine:init", function () {
  "use strict";
  var PT_KE_MM = 0.3528;

  window.Alpine.data("editorPiagam", function (konfig) {
    return {
      elemen: [],
      pilih: 0,
      lebarMm: konfig.lebarMm,
      tinggiMm: konfig.tinggiMm,
      versi: Date.now(),
      pesan: "",
      galat: false,
      berubah: false,
      menyimpan: false,
      _seret: null,
      mulai: function () {
        var data = document.getElementById("data-elemen");
        this.elemen = JSON.parse((data && data.textContent) || "[]");
        var self = this;
        window.addEventListener("pointermove", function (e) { self.gerak(e); });
        window.addEventListener("pointerup", function () { self.lepas(); });
        window.addEventListener("beforeunload", function (e) { if (self.berubah) { e.preventDefault(); e.returnValue = ""; } });
      },
      urlGambar: function () { return konfig.urlPratinjau + "?v=" + this.versi; },
      kotak: function (e) {
        var tinggiBaris = (Number(e.ukuran) || 14) * PT_KE_MM;
        var baris = Number(e.baris_maks) || 1;
        var atas = (Number(e.y) || 0) - tinggiBaris * 0.85;
        return "left:" + ((Number(e.x) || 0) / this.lebarMm * 100) + "%;top:" + (atas / this.tinggiMm * 100) +
          "%;width:" + ((Number(e.lebar) || 10) / this.lebarMm * 100) + "%;height:" + (tinggiBaris * (1 + 0.3 * (baris - 1)) * 1.15 / this.tinggiMm * 100) + "%";
      },
      tekan: function (i, ev) {
        this.pilih = i;
        var kanvas = this.$refs.kanvas.getBoundingClientRect();
        this._seret = { i: i, x0: ev.clientX, y0: ev.clientY, ex: Number(this.elemen[i].x), ey: Number(this.elemen[i].y), skala: this.lebarMm / kanvas.width };
        ev.preventDefault();
      },
      gerak: function (ev) {
        if (!this._seret) { return; }
        var s = this._seret;
        var e = this.elemen[s.i];
        e.x = Math.round((s.ex + (ev.clientX - s.x0) * s.skala) * 2) / 2;
        e.y = Math.round((s.ey + (ev.clientY - s.y0) * s.skala) * 2) / 2;
        this.berubah = true;
      },
      lepas: function () { this._seret = null; },
      geser: function (dx, dy) {
        var e = this.elemen[this.pilih];
        if (!e) { return; }
        e.x = Math.round((Number(e.x) + dx) * 2) / 2;
        e.y = Math.round((Number(e.y) + dy) * 2) / 2;
        this.berubah = true;
      },
      tengahkan: function () {
        var e = this.elemen[this.pilih];
        if (!e) { return; }
        e.x = Math.round((this.lebarMm - Number(e.lebar)) / 2 * 2) / 2;
        e.rata = "TENGAH";
        this.berubah = true;
      },
      tambah: function () {
        this.elemen.push({ kode: "teks", teks: "Teks baru", x: 20, y: this.tinggiMm / 2, lebar: this.lebarMm - 40, font: "INTER", ukuran: 14, ukuran_min: 9, warna: "#1F2937", rata: "TENGAH", baris_maks: 1, kapital: false });
        this.pilih = this.elemen.length - 1;
        this.berubah = true;
      },
      hapus: function () {
        if (!this.elemen.length || !window.confirm("Hapus elemen teks ini?")) { return; }
        this.elemen.splice(this.pilih, 1);
        this.pilih = Math.max(0, this.pilih - 1);
        this.berubah = true;
      },
      sisip: function (kunci) {
        var e = this.elemen[this.pilih];
        if (!e) { return; }
        e.teks = (e.teks || "") + "{" + kunci + "}";
        this.berubah = true;
      },
      simpan: function () {
        var self = this;
        this.menyimpan = true;
        fetch(konfig.urlSimpan, {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json", "X-CSRFToken": window.SIGAP.csrf(), "X-Requested-With": "XMLHttpRequest" },
          body: JSON.stringify(this.elemen)
        }).then(function (r) { return r.json(); }).then(function (j) {
          self.galat = !j.ok;
          self.pesan = j.ok ? "Tersimpan. Pratinjau diperbarui." : (j.pesan || "Gagal menyimpan.");
          if (j.ok) { self.berubah = false; self.versi = Date.now(); }
        }).catch(function () {
          self.galat = true;
          self.pesan = "Tidak bisa menyimpan (sinyal/sesi). Coba lagi.";
        }).finally(function () { self.menyimpan = false; });
      }
    };
  });
});
