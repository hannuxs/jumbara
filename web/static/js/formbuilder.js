/* Form builder (superadmin): urutkan kolom dengan seret/tombol, editor rumus dengan cek langsung. */
document.addEventListener("alpine:init", function () {
  "use strict";

  function kirimJson(url, data) {
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": window.SIGAP.csrf(), "X-Requested-With": "XMLHttpRequest" },
      body: JSON.stringify(data)
    }).then(function (r) { return r.json().catch(function () { return { ok: false, pesan: "Server bermasalah (" + r.status + ")." }; }); });
  }

  window.Alpine.data("urutKolom", function (url) {
    return {
      diseret: null,
      pesan: "",
      galat: false,
      _timer: null,
      mulaiSeret: function (e) {
        this.diseret = e.target.closest("li");
        e.dataTransfer.effectAllowed = "move";
        try { e.dataTransfer.setData("text/plain", this.diseret.dataset.id); } catch (x) { /* abaikan */ }
        this.diseret.classList.add("opacity-50");
      },
      seretLewat: function (e) {
        var li = e.target.closest("li");
        if (!this.diseret || !li || li === this.diseret) { return; }
        var kotak = li.getBoundingClientRect();
        var sesudah = e.clientY > kotak.top + kotak.height / 2;
        li.parentNode.insertBefore(this.diseret, sesudah ? li.nextSibling : li);
      },
      lepas: function () {
        if (!this.diseret) { return; }
        this.diseret.classList.remove("opacity-50");
        this.diseret = null;
        this.simpan();
      },
      geser: function (li, arah) {
        var tujuan = arah < 0 ? li.previousElementSibling : li.nextElementSibling;
        if (!tujuan) { return; }
        li.parentNode.insertBefore(li, arah < 0 ? tujuan : tujuan.nextSibling);
        this.simpan();
      },
      simpan: function () {
        var self = this;
        clearTimeout(this._timer);
        this._timer = setTimeout(function () {
          var id = Array.prototype.map.call(self.$refs.daftar.querySelectorAll("li[data-id]"), function (li) { return parseInt(li.dataset.id, 10); });
          kirimJson(url, id).then(function (j) {
            self.galat = !j.ok;
            self.pesan = j.ok ? "Urutan disimpan." : (j.pesan || "Urutan gagal disimpan.");
          }).catch(function () { self.galat = true; self.pesan = "Tidak ada sinyal. Urutan belum disimpan."; });
        }, 400);
      }
    };
  });

  window.Alpine.data("editorKolom", function (awalJenis, urlCek) {
    return {
      jenis: awalJenis,
      rumus: "",
      cek: { status: "", pesan: "", contoh: [] },
      _timer: null,
      mulai: function () {
        this.rumus = (this.$refs.rumus && this.$refs.rumus.value) || "";
        if (this.jenis === "RUMUS" && this.rumus) { this.periksa(); }
      },
      sisip: function (teks) {
        var el = this.$refs.rumus;
        if (!el) { return; }
        var a = el.selectionStart || el.value.length;
        var b = el.selectionEnd || a;
        el.value = el.value.slice(0, a) + teks + el.value.slice(b);
        el.focus();
        el.selectionStart = el.selectionEnd = a + teks.length;
        this.rumus = el.value;
        this.periksa();
      },
      periksa: function () {
        var self = this;
        clearTimeout(this._timer);
        if (!this.rumus.trim()) { this.cek = { status: "", pesan: "", contoh: [] }; return; }
        this.cek.status = "memeriksa";
        this._timer = setTimeout(function () {
          var kode = (document.getElementById("isian-kode") || {}).value || "";
          kirimJson(urlCek, { kode: kode, rumus: self.rumus }).then(function (j) {
            self.cek = { status: j.ok ? "ok" : "galat", pesan: j.pesan || "", contoh: j.contoh || [] };
          }).catch(function () { self.cek = { status: "galat", pesan: "Tidak bisa memeriksa (sinyal).", contoh: [] }; });
        }, 400);
      }
    };
  });
});
