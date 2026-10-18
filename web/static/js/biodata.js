/* Form biodata publik (Alpine.js). Server tetap memvalidasi semuanya; skrip ini hanya membantu:
 * cari sekolah, tingkat otomatis, peringatan lembut, draf di HP, pemotong foto 3:4,
 * ringkasan sebelum kirim, dan unggah dengan persen.
 */
document.addEventListener("alpine:init", function () {
  "use strict";
  var KUNCI_DRAF = "sigap:biodata:draf";
  var KUNCI_LANJUTAN = "sigap:biodata:lanjutan";
  var TIDAK_DISIMPAN = ["csrfmiddlewaretoken", "token", "foto", "foto_potong", "situs_web"];
  var USIA_WAJAR = { MULA: [8, 13], MADYA: [11, 16], WIRA: [14, 19] };
  var LABEL_TINGKAT = { MULA: "Mula", MADYA: "Madya", WIRA: "Wira" };
  var BATAS_FOTO = 5 * 1024 * 1024;
  var SISI_MAKS = 1600;

  function S() { return window.SIGAP ? window.SIGAP.simpan : null; }

  window.Alpine.data("formBiodata", function () {
    return {
      js: true,
      cari: "",
      bukaCari: false,
      daftarSekolah: [],
      tingkatDipilih: "",
      peranDewasa: false,
      peringatanUsia: "",
      nikDobel: false,
      adaDraf: false,
      umum: [],
      ringkasan: [],
      peringatanRingkasan: [],
      mengirim: false,
      persen: 0,
      fotoStatus: "",
      namaFoto: "",
      fotoBlob: null,
      pratinjauFoto: "",
      cropper: null,

      mulai: function () {
        var self = this;
        var pilih = this.$refs.kontingen;
        Array.prototype.forEach.call(pilih.options, function (o) {
          if (o.value) { self.daftarSekolah.push({ id: o.value, nama: o.textContent.trim(), tingkat: o.dataset.tingkat }); }
        });
        // Daftar sekolah hanya berisi sekolah dari tingkat yang dipilih (REVISI R1).
        this.saringSekolah();
        var bound = this.$root.dataset.bound === "1";
        if (!bound) {
          var params = new URLSearchParams(location.search);
          var lanjutan = S() && S().json(KUNCI_LANJUTAN, null);
          if (params.get("lagi") && lanjutan) {
            this.isiNilai(lanjutan);
          } else {
            var draf = S() && S().json(KUNCI_DRAF, null);
            if (draf && Object.keys(draf).length > 1) { this.adaDraf = true; }
          }
        } else {
          this.gulirKeGalat();
        }
        this.periksaSemua();
      },

      // --- Sekolah dan tingkat ------------------------------------------------
      hasilCari: function () {
        // Kosong = tampilkan semua sekolah tingkat terpilih; diketik = saring per kata.
        var kata = this.cari.toLowerCase().trim().split(/\s+/).filter(Boolean), tingkat = this.tingkatDipilih;
        return this.daftarSekolah.filter(function (k) {
          if (k.tingkat !== tingkat) { return false; }
          var n = k.nama.toLowerCase();
          return kata.every(function (w) { return n.indexOf(w) !== -1; });
        });
      },
      labelTingkat: function () { return LABEL_TINGKAT[this.tingkatDipilih] || ""; },
      jumlahSekolah: function () {
        var t = this.tingkatDipilih;
        return this.daftarSekolah.filter(function (k) { return k.tingkat === t; }).length;
      },
      pilihPertama: function () {
        var hasil = this.hasilCari();
        if (hasil.length) { this.pilihSekolah(hasil[0].id); }
      },
      pilihSekolah: function (id) {
        this.$refs.kontingen.value = id;
        this.cari = "";
        this.bukaCari = false;
        this.sekolahBerubah();
        this.simpanDraf();
      },
      // Bangun ulang pilihan sekolah sesuai tingkat. Opsi dihapus/ditambah (bukan disembunyikan),
      // karena <option hidden> tidak berlaku di Safari iPhone.
      saringSekolah: function () {
        var pilih = this.$refs.kontingen, lama = pilih.value, tingkat = this.nilai("tingkat");
        this.tingkatDipilih = tingkat;
        while (pilih.firstChild) { pilih.removeChild(pilih.firstChild); }
        var kosong = document.createElement("option");
        kosong.value = "";
        kosong.textContent = tingkat ? "Pilih sekolah tingkat " + LABEL_TINGKAT[tingkat] : "Pilih tingkat dulu";
        pilih.appendChild(kosong);
        var masihAda = false;
        this.daftarSekolah.forEach(function (k) {
          if (k.tingkat !== tingkat) { return; }
          var o = document.createElement("option");
          o.value = k.id;
          o.textContent = k.nama;
          o.dataset.tingkat = k.tingkat;
          if (k.id === lama) { o.selected = true; masihAda = true; }
          pilih.appendChild(o);
        });
        if (!masihAda) { pilih.value = ""; }
        pilih.disabled = !tingkat;
      },
      tingkatBerubah: function () {
        this.saringSekolah();
        this.cari = "";
        this.bukaCari = false;
        this.hapusGalat("tingkat");
        this.periksaSemua();
      },
      sekolahBerubah: function () {
        this.hapusGalat("kontingen");
        this.periksaSemua();
      },

      nilai: function (nama) {
        var f = this.$refs.form;
        var el = f.elements[nama];
        if (!el) { return ""; }
        if (el instanceof RadioNodeList) { return el.value || ""; }
        if (el.type === "checkbox") { return el.checked ? "on" : ""; }
        return (el.value || "").trim();
      },

      tanggalLahir: function () {
        var h = parseInt(this.nilai("tanggal_lahir_0"), 10), b = parseInt(this.nilai("tanggal_lahir_1"), 10), t = parseInt(this.nilai("tanggal_lahir_2"), 10);
        if (!h || !b || !t) { return null; }
        var d = new Date(t, b - 1, h);
        if (d.getMonth() !== b - 1) { return null; }
        return { h: h, b: b, t: t };
      },

      periksaSemua: function () {
        var tingkat = this.nilai("tingkat");
        var peran = this.nilai("peran");
        this.peranDewasa = peran === "PIMPINAN_KONTINGEN" || peran === "PEMBINA_PENDAMPING";

        var tgl = this.tanggalLahir();

        this.peringatanUsia = "";
        if (tgl && peran) {
          var acuan = (this.$root.dataset.usiaAcuan || "2026-11-12").split("-").map(Number);
          var usia = acuan[0] - tgl.t - ((acuan[1] < tgl.b || (acuan[1] === tgl.b && acuan[2] < tgl.h)) ? 1 : 0);
          if (peran === "PESERTA" && USIA_WAJAR[tingkat]) {
            var r = USIA_WAJAR[tingkat];
            if (usia < r[0] || usia > r[1]) {
              this.peringatanUsia = "Usia " + usia + " tahun kurang sesuai untuk peserta tingkat " + LABEL_TINGKAT[tingkat] + " (" + r[0] + "–" + r[1] + " tahun). Periksa lagi tanggal lahir dan tingkat. Jika sudah benar, lanjutkan.";
            }
          } else if (this.peranDewasa && usia < 17) {
            this.peringatanUsia = "Usia " + usia + " tahun. Periksa lagi tanggal lahir dan peran. Jika sudah benar, lanjutkan.";
          }
        }
      },

      // --- Validasi ringan di browser (server tetap memeriksa) ------------------
      tampilGalat: function (nama, pesan) {
        var p = this.$refs.form.querySelector('[data-galat="' + nama + '"]');
        if (p) { p.textContent = pesan || ""; }
        var el = this.$refs.form.elements[nama];
        if (el && el.classList && !(el instanceof RadioNodeList)) { el.classList.toggle("input-galat", !!pesan); }
      },
      hapusGalat: function (nama) { this.tampilGalat(nama, ""); },

      aturanIsian: function (nama, v) {
        var dewasa = this.peranDewasa;
        var telp = /^(\+?62|0)?8\d{7,12}$/;
        switch (nama) {
          case "nama_lengkap":
            if (!v) { return "Nama lengkap wajib diisi."; }
            if (v.length < 3) { return "Nama terlalu pendek (minimal 3 huruf)."; }
            if (/[0-9_@#$%^&*()+=\[\]{};:"\\|<>\/?!~`]/.test(v)) { return "Nama hanya boleh berisi huruf, spasi, titik, koma, apostrof ('), dan tanda hubung (-)."; }
            return "";
          case "nik":
            if (!v) { return "NIK wajib diisi."; }
            if (v.length !== 16) { return "NIK harus tepat 16 angka (sekarang " + v.length + " angka)."; }
            if (/^(\d)\1+$/.test(v)) { return "NIK tidak valid. Periksa lagi di Kartu Keluarga."; }
            return "";
          case "tempat_lahir":
            if (!v) { return "Tempat lahir wajib diisi."; }
            if (v.length < 2) { return "Tempat lahir 2 sampai 60 huruf."; }
            return "";
          case "alamat":
            if (!v) { return "Alamat rumah wajib diisi."; }
            if (v.length < 10) { return "Alamat terlalu pendek (minimal 10 karakter). Tulis jalan, RT, desa/kelurahan."; }
            return "";
          case "telepon":
            if (!v) { return dewasa ? "Nomor HP wajib diisi untuk Pimpinan Kontingen dan Pembina Pendamping." : ""; }
            return telp.test(v.replace(/[\s\-().]/g, "")) ? "" : "Nomor HP tidak valid. Contoh: 081234567890.";
          case "nama_orang_tua":
            if (!v) { return dewasa ? "" : "Nama ayah/ibu/wali wajib diisi."; }
            return v.length < 3 ? "Nama orang tua/wali hanya huruf, minimal 3 huruf." : "";
          case "telepon_orang_tua":
            if (!v) { return dewasa ? "" : "Nomor HP ayah/ibu/wali wajib diisi."; }
            return telp.test(v.replace(/[\s\-().]/g, "")) ? "" : "Nomor HP tidak valid. Contoh: 081234567890.";
        }
        return "";
      },
      cekIsian: function (el) {
        this.periksaSemua();
        if (!el.value.trim()) { return; } // isian kosong baru dinilai saat kirim
        this.tampilGalat(el.name, this.aturanIsian(el.name, el.value.trim()));
      },
      validasiSemua: function () {
        var self = this, galat = {};
        var wajibPilih = { kontingen: "Pilih utusan sekolah.", tingkat: "Pilih tingkat.", peran: "Pilih peran Anda.", jenis_kelamin: "Pilih jenis kelamin.", golongan_darah: "Pilih golongan darah (pilih \u201cBelum tahu\u201d jika tidak tahu)." };
        Object.keys(wajibPilih).forEach(function (n) { if (!self.nilai(n)) { galat[n] = wajibPilih[n]; } });
        ["nama_lengkap", "nik", "tempat_lahir", "alamat", "telepon", "nama_orang_tua", "telepon_orang_tua"].forEach(function (n) {
          var p = self.aturanIsian(n, self.nilai(n));
          if (p) { galat[n] = p; }
        });
        if (!this.tanggalLahir()) { galat.tanggal_lahir = "Pilih tanggal, bulan, dan tahun lahir."; }
        var foto = this.$refs.form.elements.foto;
        if (foto.required && !this.fotoBlob && !(foto.files && foto.files.length)) { galat.foto = "Foto wajib diunggah."; }
        if (!this.nilai("persetujuan")) { galat.persetujuan = "Centang pernyataan ini untuk melanjutkan."; }
        ["kontingen", "tingkat", "peran", "nama_lengkap", "nik", "jenis_kelamin", "tempat_lahir", "tanggal_lahir", "alamat", "golongan_darah", "telepon", "nama_orang_tua", "telepon_orang_tua", "foto", "persetujuan"].forEach(function (n) {
          self.tampilGalat(n, galat[n] || "");
        });
        return galat;
      },
      gulirKeGalat: function () {
        var self = this;
        setTimeout(function () {
          var p = Array.prototype.find.call(self.$refs.form.querySelectorAll("[data-galat]"), function (x) { return x.textContent.trim(); });
          var target = p ? p.closest("[data-isian]") : self.$refs.galatUmum;
          if (target) { target.scrollIntoView({ behavior: "smooth", block: "center" }); }
          var masukan = target && target.querySelector("input:not([type=radio]):not([type=checkbox]),select,textarea");
          if (masukan) { try { masukan.focus({ preventScroll: true }); } catch (e) { /* abaikan */ } }
        }, 50);
      },

      // --- Draf di HP -----------------------------------------------------------
      simpanDraf: function () {
        if (!S()) { return; }
        var data = {}, f = this.$refs.form;
        Array.prototype.forEach.call(f.elements, function (el) {
          if (!el.name || TIDAK_DISIMPAN.indexOf(el.name) !== -1) { return; }
          if ((el.type === "radio" || el.type === "checkbox") && !el.checked) { return; }
          data[el.name] = el.type === "checkbox" ? "on" : el.value;
        });
        data._disimpan = Date.now();
        S().tulisJson(KUNCI_DRAF, data);
      },
      isiNilai: function (data) {
        var f = this.$refs.form;
        // Tingkat diisi dulu agar pilihan sekolahnya tersedia sebelum sekolah dipilih.
        if (data.tingkat) {
          Array.prototype.forEach.call(f.elements.tingkat, function (r) { r.checked = r.value === data.tingkat; });
          this.saringSekolah();
        }
        Object.keys(data).forEach(function (nama) {
          if (nama.charAt(0) === "_" || nama === "tingkat") { return; }
          var el = f.elements[nama];
          if (!el) { return; }
          if (el instanceof RadioNodeList) {
            Array.prototype.forEach.call(el, function (r) { r.checked = r.value === data[nama]; });
          } else if (el.type === "checkbox") {
            el.checked = data[nama] === "on";
          } else if (el.type !== "file") {
            el.value = data[nama];
          }
        });
        this.periksaSemua();
      },
      pakaiDraf: function () {
        this.isiNilai(S().json(KUNCI_DRAF, {}));
        this.adaDraf = false;
      },
      buangDraf: function () {
        S().hapus(KUNCI_DRAF);
        this.adaDraf = false;
      },

      // --- Foto -----------------------------------------------------------------
      fotoDipilih: function (e) {
        var self = this, file = e.target.files && e.target.files[0];
        this.hapusGalat("foto");
        this.fotoBlob = null;
        if (this.cropper) { this.cropper.destroy(); this.cropper = null; }
        if (!file) { this.fotoStatus = ""; return; }
        if (["image/jpeg", "image/png", "image/jpg", "image/pjpeg"].indexOf(file.type) === -1 && !/\.(jpe?g|png)$/i.test(file.name)) {
          this.tampilGalat("foto", "Foto harus berformat JPG atau PNG.");
          e.target.value = "";
          this.fotoStatus = "";
          return;
        }
        if (file.size > BATAS_FOTO) {
          this.tampilGalat("foto", "Ukuran foto lebih dari 5 MB (" + (file.size / 1048576).toFixed(1) + " MB). Pilih foto yang lebih kecil, atau ambil ulang foto dengan kamera.");
          e.target.value = "";
          this.fotoStatus = "";
          return;
        }
        if (!window.Cropper || !window.HTMLCanvasElement || !HTMLCanvasElement.prototype.toBlob) { this.fotoStatus = ""; return; }
        this.fotoStatus = "memuat";
        var url = URL.createObjectURL(file);
        var img = new Image();
        img.onload = function () {
          // Browser modern sudah meluruskan orientasi EXIF saat menggambar ke canvas.
          var skala = Math.min(1, SISI_MAKS / Math.max(img.naturalWidth, img.naturalHeight));
          var c = document.createElement("canvas");
          c.width = Math.round(img.naturalWidth * skala);
          c.height = Math.round(img.naturalHeight * skala);
          var ctx = c.getContext("2d");
          ctx.fillStyle = "#fff";
          ctx.fillRect(0, 0, c.width, c.height);
          ctx.drawImage(img, 0, 0, c.width, c.height);
          URL.revokeObjectURL(url);
          c.toBlob(function (blob) {
            if (!blob) { self.fotoStatus = ""; return; }
            self.fotoBlob = blob;
            self.fotoStatus = "potong";
            self.$nextTick(function () { self.pasangCropper(URL.createObjectURL(blob)); });
          }, "image/jpeg", 0.85);
        };
        img.onerror = function () {
          URL.revokeObjectURL(url);
          self.fotoStatus = "";
          self.tampilGalat("foto", "Foto tidak bisa dibuka. Pilih foto JPG atau PNG lain.");
          e.target.value = "";
        };
        img.src = url;
      },
      pasangCropper: function (src) {
        var el = this.$refs.gambarPotong;
        el.src = src;
        this.cropper = new window.Cropper(el, {
          aspectRatio: 3 / 4, viewMode: 1, autoCropArea: 0.9, dragMode: "move",
          checkOrientation: false, background: false, responsive: true, movable: true, zoomable: true, rotatable: true
        });
      },
      putar: function () { if (this.cropper) { this.cropper.rotate(90); } },
      gantiFoto: function () {
        var f = this.$refs.form.elements.foto;
        f.value = "";
        if (this.cropper) { this.cropper.destroy(); this.cropper = null; }
        this.fotoBlob = null;
        this.fotoStatus = "";
        f.click();
      },
      dataPotong: function () {
        if (!this.cropper) { return ""; }
        var d = this.cropper.getData(true);
        return JSON.stringify({ x: d.x, y: d.y, w: d.width, h: d.height, r: d.rotate || 0 });
      },

      // --- Ringkasan dan kirim --------------------------------------------------
      teksPilihan: function (nama) {
        var f = this.$refs.form, el = f.elements[nama];
        if (!el) { return ""; }
        if (el instanceof RadioNodeList) {
          var r = Array.prototype.find.call(el, function (x) { return x.checked; });
          if (!r) { return ""; }
          var span = r.parentNode.querySelector("span");
          if (span && span.querySelector("span")) { span = span.querySelector("span"); }
          return span ? span.textContent.trim() : r.value;
        }
        if (el.tagName === "SELECT") { return el.selectedOptions[0] ? el.selectedOptions[0].textContent.trim() : ""; }
        return el.value.trim();
      },
      tampilkanRingkasan: function () {
        if (this.mengirim) { return; }
        this.umum = [];
        this.periksaSemua();
        var galat = this.validasiSemua();
        if (Object.keys(galat).length) {
          this.umum = ["Ada isian yang perlu diperbaiki. Lihat tulisan merah."];
          this.gulirKeGalat();
          return;
        }
        var nik = this.nilai("nik");
        var tgl = this.tanggalLahir();
        var bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];
        var b = [
          { label: "Sekolah", nilai: this.teksPilihan("kontingen") },
          { label: "Tingkat", nilai: this.teksPilihan("tingkat") },
          { label: "Peran", nilai: this.teksPilihan("peran") },
          { label: "Nama lengkap", nilai: this.nilai("nama_lengkap").toUpperCase() },
          { label: "NIK", nilai: nik.slice(0, 4) + "********" + nik.slice(-4) },
          { label: "No. anggota", nilai: this.nilai("nomor_induk_anggota") || "-" },
          { label: "Jenis kelamin", nilai: this.teksPilihan("jenis_kelamin") },
          { label: "Tempat, tgl lahir", nilai: this.nilai("tempat_lahir") + ", " + tgl.h + " " + bulan[tgl.b - 1] + " " + tgl.t },
          { label: "Alamat", nilai: this.nilai("alamat") },
          { label: "Golongan darah", nilai: this.teksPilihan("golongan_darah") },
          { label: "Nomor HP", nilai: this.nilai("telepon") || "-" },
          { label: "Orang tua/wali", nilai: this.nilai("nama_orang_tua").toUpperCase() || "-" },
          { label: "HP orang tua/wali", nilai: this.nilai("telepon_orang_tua") || "-" }
        ];
        this.peringatanRingkasan = [];
        if (this.peringatanUsia) { this.peringatanRingkasan.push(this.peringatanUsia); }
        this.pratinjauFoto = "";
        if (this.cropper) {
          try { this.pratinjauFoto = this.cropper.getCroppedCanvas({ width: 150, height: 200 }).toDataURL("image/jpeg", 0.8); } catch (e) { /* abaikan */ }
        }
        this.ringkasan = b;
      },
      kirim: function () {
        var self = this, f = this.$refs.form;
        this.ringkasan = [];
        this.mengirim = true;
        this.persen = 0;
        var fd = new FormData(f);
        if (this.fotoBlob) {
          fd.set("foto", this.fotoBlob, "foto.jpg");
          fd.set("foto_potong", this.dataPotong());
        }
        var xhr = new XMLHttpRequest();
        xhr.open("POST", f.action);
        xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
        xhr.setRequestHeader("X-CSRFToken", f.elements.csrfmiddlewaretoken.value);
        xhr.timeout = 180000;
        xhr.upload.onprogress = function (e) { if (e.lengthComputable) { self.persen = Math.round(e.loaded / e.total * 100); } };
        xhr.onload = function () {
          var data = null;
          try { data = JSON.parse(xhr.responseText); } catch (e) { data = null; }
          if (data && data.ok) {
            if (S()) {
              S().hapus(KUNCI_DRAF);
              S().tulisJson(KUNCI_LANJUTAN, { kontingen: self.nilai("kontingen"), tingkat: self.nilai("tingkat") });
            }
            window.location.href = data.url;
            return;
          }
          self.mengirim = false;
          if (!data) {
            self.umum = xhr.status === 403
              ? ["Halaman sudah terlalu lama terbuka. Muat ulang halaman (isian tetap tersimpan), lalu kirim lagi."]
              : ["Terjadi gangguan (kode " + xhr.status + "). Isian tetap tersimpan di HP. Coba kirim lagi sebentar lagi."];
            self.gulirKeGalat();
            return;
          }
          if (data.token) { f.elements.token.value = data.token; }
          self.nikDobel = !!data.nik_dobel;
          self.umum = data.umum && data.umum.length ? data.umum : ["Ada isian yang perlu diperbaiki. Lihat tulisan merah."];
          Object.keys(data.galat || {}).forEach(function (n) {
            var nama = n === "tanggal_lahir" ? "tanggal_lahir" : n;
            self.tampilGalat(nama, data.galat[n][0]);
          });
          self.gulirKeGalat();
        };
        xhr.onerror = xhr.ontimeout = function () {
          self.mengirim = false;
          self.umum = ["Koneksi terputus. Isian tetap tersimpan di HP. Periksa sinyal, lalu tekan Kirim lagi."];
          self.gulirKeGalat();
        };
        xhr.send(fd);
      }
    };
  });
});
