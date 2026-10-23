/* Mengisi form builder: draf di localStorage, cek batas angka, ringkasan sebelum kirim. */
document.addEventListener("alpine:init", function () {
  "use strict";

  function angkaId(teks) {
    return String(Number(teks)).replace(".", ",");
  }
  function bacaDraf(kunci) {
    try { return JSON.parse(localStorage.getItem(kunci) || "null"); } catch (e) { return null; }
  }
  function tulisDraf(kunci, data) {
    try {
      if (data === null) { localStorage.removeItem(kunci); } else { localStorage.setItem(kunci, JSON.stringify(data)); }
    } catch (e) { /* penyimpanan tidak tersedia */ }
  }

  window.Alpine.data("isianForm", function (kunciDraf, penilaian) {
    return {
      batas: {},
      ringkas: { buka: false, baris: [] },
      _yakin: false,
      mulai: function () {
        var uuid = window.SIGAP && window.SIGAP.uuid ? window.SIGAP.uuid() : String(Date.now()) + Math.random();
        if (!this.$refs.uuid.value) { this.$refs.uuid.value = uuid; }
        // Pulihkan draf hanya bila halaman masih kosong (bukan hasil galat dari server).
        var adaIsi = Array.prototype.some.call(this.$refs.form.querySelectorAll("input[name^=k_]:not([type=hidden]):not([type=file]), textarea[name^=k_]"), function (el) {
          return (el.type === "radio" || el.type === "checkbox") ? el.checked : el.value !== "";
        });
        var draf = bacaDraf(kunciDraf);
        if (!adaIsi && draf && draf.isi) {
          this.terapkan(draf.isi);
        }
        var self = this;
        this.$refs.form.querySelectorAll("input[data-min], input[data-max]").forEach(function (el) { self.cekBatas(el); });
      },
      terapkan: function (isi) {
        var form = this.$refs.form;
        Object.keys(isi).forEach(function (nama) {
          if (nama === "nama_pengisi" && form.elements[nama] && form.elements[nama].value) { return; }
          var el = form.elements[nama];
          if (!el) { return; }
          var nilai = isi[nama];
          if (el.length !== undefined && el.tagName !== "SELECT") {
            Array.prototype.forEach.call(el, function (x) { x.checked = Array.isArray(nilai) ? nilai.indexOf(x.value) !== -1 : x.value === nilai; });
          } else if (el.type === "checkbox") {
            el.checked = Array.isArray(nilai) ? nilai.indexOf(el.value) !== -1 : !!nilai;
          } else if (el.type === "radio") {
            el.checked = el.value === nilai;
          } else {
            el.value = nilai;
          }
        });
      },
      simpanDraf: function () {
        var form = this.$refs.form;
        var isi = {};
        Array.prototype.forEach.call(form.elements, function (el) {
          if (!el.name || el.type === "file" || el.type === "hidden" || el.name === "csrfmiddlewaretoken") { return; }
          if (el.type === "radio") { if (el.checked) { isi[el.name] = el.value; } return; }
          if (el.type === "checkbox") {
            isi[el.name] = isi[el.name] || [];
            if (el.checked) { isi[el.name].push(el.value); }
            return;
          }
          isi[el.name] = el.value;
        });
        tulisDraf(kunciDraf, { isi: isi, waktu: Date.now() });
      },
      cekBatas: function (el) {
        var teks = (el.value || "").trim().replace(",", ".");
        var pesan = "";
        if (teks !== "") {
          var n = Number(teks);
          if (isNaN(n)) { pesan = "Isi dengan angka."; }
          else if (el.dataset.min !== undefined && n < Number(el.dataset.min)) { pesan = "Paling kecil " + angkaId(el.dataset.min) + "."; }
          else if (el.dataset.max !== undefined && n > Number(el.dataset.max)) { pesan = "Paling besar " + angkaId(el.dataset.max) + "."; }
        }
        this.batas[el.name] = pesan;
      },
      kirim: function (e) {
        if (this._yakin) { tulisDraf(kunciDraf, null); return; }
        e.preventDefault();
        var galatBatas = Object.keys(this.batas).filter(function (k) { return this.batas[k]; }, this);
        if (galatBatas.length) {
          var el = this.$refs.form.elements[galatBatas[0]];
          if (el) { el.focus(); el.scrollIntoView({ block: "center" }); }
          return;
        }
        this.ringkas.baris = this.susunRingkas();
        this.ringkas.buka = true;
      },
      kirimSungguh: function () {
        this._yakin = true;
        this.ringkas.buka = false;
        var form = this.$refs.form;
        tulisDraf(kunciDraf, null);
        if (form.requestSubmit) { form.requestSubmit(); } else { form.submit(); }
      },
      susunRingkas: function () {
        var form = this.$refs.form;
        var baris = [];
        form.querySelectorAll("[data-isian], [data-subjek]").forEach(function (blok) {
          if (blok.hasAttribute("data-subjek")) { baris.push({ label: "Subjek", nilai: blok.textContent.trim() }); return; }
          var labelEl = blok.querySelector("label.label, legend");
          var label = labelEl ? labelEl.textContent.trim() : blok.dataset.isian;
          var nilai = [];
          blok.querySelectorAll("input, select, textarea").forEach(function (el) {
            if (el.type === "hidden") { return; }
            if (el.type === "radio" || el.type === "checkbox") {
              if (el.checked) { var t = el.closest("label"); nilai.push(t ? t.textContent.trim() : el.value); }
            } else if (el.type === "file") {
              if (el.files && el.files[0]) { nilai.push(el.files[0].name); }
            } else if (el.tagName === "SELECT") {
              if (el.value) { nilai.push(el.options[el.selectedIndex].text); }
            } else if (el.value) {
              nilai.push(el.value);
            }
          });
          baris.push({ label: label, nilai: nilai.length ? nilai.join(", ") : "(kosong)" });
        });
        return baris;
      }
    };
  });
});
