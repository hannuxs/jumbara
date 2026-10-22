/* Pemindai kehadiran (akun panitia/superadmin). docs/14-ABSENSI.md
 *
 * Setiap pindaian disimpan dulu di IndexedDB (antrean) dengan client_uuid, baru dikirim ke server.
 * Bila gagal karena sinyal/sesi, pindaian tetap di HP (abu-abu, "menunggu terkirim") dan dikirim
 * otomatis: setiap 10 detik, saat kembali online, saat halaman dibuka, dan setelah masuk lagi.
 * Server idempoten menurut client_uuid, jadi kiriman ulang tidak membuat data dobel.
 */
document.addEventListener("alpine:init", function () {
  "use strict";
  var KUNCI_LOCK_MS = 3000;
  var TAMPIL_HIJAU_MS = 1500;
  var TAMPIL_LAIN_MS = 3000;
  var BATAS_BATCH = 50;
  var BATAS_SEDANG_KIRIM_MS = 10000; // lebih lama dari batas waktu kirim (8 detik)
  var LABEL_TINGKAT = { MULA: "Mula", MADYA: "Madya", WIRA: "Wira", SEMUA: "Semua tingkat" };
  var NAMA_HARI = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"];

  var idb = window.idbKeyval;
  var tokoAntrean = idb ? idb.createStore("sigap-pemindai", "antrean") : null;
  var tokoCache = idb ? idb.createStore("sigap-pemindai-cache", "peserta") : null;

  function sekarangIso() {
    // ISO dengan zona waktu HP; server mengubahnya ke WITA.
    return new Date().toISOString();
  }
  function jamSekarang() {
    var d = new Date();
    return ("0" + d.getHours()).slice(-2) + "." + ("0" + d.getMinutes()).slice(-2);
  }

  async function sha16(teks) {
    if (!window.crypto || !window.crypto.subtle) { return ""; }
    var data = new TextEncoder().encode(teks);
    var buf = await window.crypto.subtle.digest("SHA-256", data);
    return Array.prototype.map.call(new Uint8Array(buf), function (b) { return ("0" + b.toString(16)).slice(-2); }).join("").slice(0, 16);
  }

  window.Alpine.data("pemindai", function () {
    return {
      tahap: "nama",
      namaPemindai: "",
      isianNama: "",
      superadmin: false,
      daftarTitik: [],
      memuatTitik: false,
      galatTitik: "",
      cariTitik: "",
      titik: null,
      titikTutup: false,
      ringkas: { hadir: 0, kontingen_hadir: 0, kontingen_total: 0, terakhir: [] },
      riwayat: [],
      menunggu: 0,
      daring: navigator.onLine,
      sesiHabis: false,
      hasil: null,
      _timerHasil: null,
      // kamera
      scanner: null,
      kamera: [],
      indeksKamera: 0,
      kameraAktif: false,
      pesanKamera: "",
      adaSenter: false,
      senterNyala: false,
      suara: true,
      _kunciQr: {},
      _wakeLock: null,
      _audio: null,
      _cache: null,
      _timerKirim: null,
      _timerRingkas: null,
      _mengirim: false,
      cari: { buka: false, q: "", hasil: [], memuat: false },

      // --- Mulai ------------------------------------------------------------
      mulai: function () {
        var self = this;
        this.superadmin = this.$root.dataset.superadmin === "1";
        this.namaPemindai = window.SIGAP.namaPelaku();
        this.isianNama = this.namaPemindai;
        var ing = window.SIGAP.ingatan();
        if (ing.suara === false) { this.suara = false; }
        if (typeof ing.kamera === "number") { this.indeksKamera = ing.kamera; }
        if (!this.namaPemindai) {
          this.tahap = "nama";
          this.$nextTick(function () { self.$refs.isianNama.focus(); });
        } else {
          this.tahap = "titik";
        }
        this.muatTitik().then(function () {
          // Kembali ke titik absen terakhir di perangkat ini.
          var terakhir = window.SIGAP.ingatan().titik_absen_terakhir;
          if (self.namaPemindai && terakhir) {
            var t = self.daftarTitik.find(function (x) { return x.id === terakhir; });
            if (t) { self.pilihTitik(t); }
          }
        });
        this.hitungAntrean();
        this.kirimAntrean(false);
        this._timerKirim = setInterval(function () { self.kirimAntrean(false); self.hitungAntrean(); }, 10000);
        window.addEventListener("online", function () { self.daring = true; self.kirimAntrean(true); });
        window.addEventListener("offline", function () { self.daring = false; });
        document.addEventListener("visibilitychange", function () {
          if (document.visibilityState === "visible" && self.tahap === "pindai") { self.kunciLayar(); self.kirimAntrean(false); }
        });
        // Jangan keluar akun bila masih ada antrean.
        document.querySelectorAll("form[data-form-keluar]").forEach(function (f) {
          f.addEventListener("submit", function (e) {
            if (self.menunggu > 0 && !window.confirm(self.menunggu + " pindaian belum terkirim dan tetap tersimpan di HP ini. Tetap keluar?")) {
              e.preventDefault();
            }
          });
        });
      },

      simpanNama: function () {
        if (!window.SIGAP.aturNama(this.isianNama)) { return; }
        this.namaPemindai = window.SIGAP.namaPelaku();
        this.tahap = this.titik ? "pindai" : "titik";
      },

      simpanPilihan: function () {
        var ing = window.SIGAP.ingatan();
        ing.suara = this.suara;
        ing.kamera = this.indeksKamera;
        if (this.titik) { ing.titik_absen_terakhir = this.titik.id; }
        window.SIGAP.simpanIngatan(ing);
      },

      // --- Titik absen ---------------------------------------------------------
      muatTitik: function () {
        var self = this;
        this.memuatTitik = true;
        this.galatTitik = "";
        return fetch("/api/titik-absen/", { credentials: "same-origin" })
          .then(function (r) {
            if (r.status === 401) { self.sesiHabis = true; throw new Error("sesi"); }
            return r.json();
          })
          .then(function (d) {
            self.daftarTitik = d.titik;
            try { localStorage.setItem("sigap:pemindai:titik", JSON.stringify(d.titik)); } catch (e) { /* abaikan */ }
          })
          .catch(function () {
            try { self.daftarTitik = JSON.parse(localStorage.getItem("sigap:pemindai:titik") || "[]"); } catch (e) { self.daftarTitik = []; }
            if (!self.daftarTitik.length) { self.galatTitik = "Daftar titik absen tidak bisa dimuat. Periksa sinyal lalu muat ulang."; }
          })
          .finally(function () { self.memuatTitik = false; });
      },
      grupTitik: function () {
        var q = this.cariTitik.toLowerCase().trim();
        var label = { BERLANGSUNG: "Sedang berlangsung", NANTI_HARI_INI: "Nanti hari ini", SUDAH_LEWAT: "Sudah lewat hari ini", HARI_LAIN: "Hari lain", TUTUP: "Ditutup" };
        var urut = ["BERLANGSUNG", "NANTI_HARI_INI", "SUDAH_LEWAT", "HARI_LAIN", "TUTUP"];
        var daftar = this.daftarTitik.filter(function (t) {
          if (!q) { return true; }
          return (t.nama + " " + t.kode + " " + (LABEL_TINGKAT[t.tingkat] || "") + " " + t.lokasi).toLowerCase().indexOf(q) !== -1;
        });
        return urut.map(function (k) {
          return { kode: k, label: label[k], titik: daftar.filter(function (t) { return t.kelompok === k; }) };
        }).filter(function (g) { return g.titik.length; });
      },
      warnaTingkat: function (t) {
        return { MULA: "bg-mula", MADYA: "bg-madya", WIRA: "bg-wira", SEMUA: "bg-gray-400" }[t] || "bg-gray-400";
      },
      labelTanggal: function (t) {
        var d = new Date(t.tanggal + "T00:00:00");
        return NAMA_HARI[d.getDay()] + " " + d.getDate() + "/" + (d.getMonth() + 1);
      },
      pilihTitik: function (t) {
        this.titik = t;
        this.titikTutup = t.kelompok !== "BERLANGSUNG";
        this.tahap = "pindai";
        this.simpanPilihan();
        this.muatCache();
        this.perbaruiRingkas();
        var self = this;
        clearInterval(this._timerRingkas);
        this._timerRingkas = setInterval(function () { self.perbaruiRingkas(); }, 10000);
        this.$nextTick(function () { self.nyalakanKamera(); });
        this.kunciLayar();
      },
      selesai: function () {
        this.matikanKamera();
        clearInterval(this._timerRingkas);
        var ing = window.SIGAP.ingatan();
        delete ing.titik_absen_terakhir;
        window.SIGAP.simpanIngatan(ing);
        this.titik = null;
        this.tahap = "titik";
        this.muatTitik();
      },
      perbaruiRingkas: function () {
        var self = this;
        if (!this.titik) { return; }
        fetch("/api/titik-absen/" + this.titik.id + "/ringkas/", { credentials: "same-origin" })
          .then(function (r) { if (r.status === 401) { self.sesiHabis = true; } return r.ok ? r.json() : null; })
          .then(function (d) { if (d) { self.ringkas = d; self.titikTutup = !d.terbuka; self.daring = true; } })
          .catch(function () { self.daring = false; });
      },

      // --- Cache nama untuk tampilan saat offline ---------------------------------
      muatCache: function () {
        var self = this;
        var kunci = "titik:" + this.titik.id;
        if (tokoCache) {
          idb.get(kunci, tokoCache).then(function (d) { if (d) { self._cache = d; } }).catch(function () {});
        }
        fetch("/api/titik-absen/" + this.titik.id + "/peserta/", { credentials: "same-origin" })
          .then(function (r) { return r.ok ? r.json() : null; })
          .then(function (d) {
            if (!d) { return; }
            self._cache = d.peserta;
            if (tokoCache) { idb.set(kunci, d.peserta, tokoCache).catch(function () {}); }
          })
          .catch(function () {});
      },
      cariDiCache: async function (qr) {
        if (!this._cache) { return null; }
        var teks = (qr || "").trim().toUpperCase();
        if (teks.indexOf("SJP:") === 0) {
          var h = await sha16(teks.slice(4));
          return this._cache.find(function (p) { return p.h === h; }) || null;
        }
        var kode = teks.replace(/[\s-]/g, "");
        if (kode.length === 8) {
          var k = kode.slice(0, 4) + "-" + kode.slice(4);
          return this._cache.find(function (p) { return p.k === k; }) || null;
        }
        return null;
      },

      // --- Kamera -----------------------------------------------------------------
      nyalakanKamera: async function () {
        var self = this;
        this.pesanKamera = "";
        if (!window.QrScanner) { this.pesanKamera = "Pustaka pemindai tidak termuat. Muat ulang halaman."; return; }
        if (!window.isSecureContext) {
          this.pesanKamera = "Kamera hanya bisa dipakai lewat alamat https://. Sementara ini gunakan tombol “Cari nama”.";
          return;
        }
        try {
          if (!this.scanner) {
            this.scanner = new window.QrScanner(this.$refs.video, function (r) { self.terbaca(r.data); }, {
              returnDetailedScanResult: true,
              highlightScanRegion: true,
              highlightCodeOutline: true,
              maxScansPerSecond: 8,
              preferredCamera: "environment"
            });
          }
          await this.scanner.start();
          this.kameraAktif = true;
          try { this.kamera = await window.QrScanner.listCameras(true); } catch (e) { this.kamera = []; }
          if (this.kamera.length > 1 && this.indeksKamera > 0 && this.kamera[this.indeksKamera]) {
            await this.scanner.setCamera(this.kamera[this.indeksKamera].id);
          }
          this.adaSenter = await this.scanner.hasFlash();
        } catch (e) {
          this.kameraAktif = false;
          var nama = (e && (e.name || e)) + "";
          if (nama.indexOf("NotAllowed") !== -1 || nama.indexOf("permission") !== -1) {
            this.pesanKamera = "Izin kamera ditolak. Chrome: ketuk ikon gembok di samping alamat > Izin > Kamera > Izinkan. Safari iPhone: Pengaturan > Safari > Kamera > Izinkan. Lalu tekan Coba lagi.";
          } else if (nama.indexOf("NotFound") !== -1 || nama.indexOf("Camera not found") !== -1) {
            this.pesanKamera = "Kamera tidak ditemukan di perangkat ini. Gunakan tombol “Cari nama”.";
          } else {
            this.pesanKamera = "Kamera tidak bisa dinyalakan (" + nama + "). Tutup aplikasi lain yang memakai kamera lalu Coba lagi.";
          }
        }
      },
      matikanKamera: function () {
        if (this.scanner) { this.scanner.stop(); }
        this.kameraAktif = false;
        this.senterNyala = false;
        if (this._wakeLock) { this._wakeLock.release().catch(function () {}); this._wakeLock = null; }
      },
      gantiKamera: async function () {
        if (!this.scanner || this.kamera.length < 2) { return; }
        this.indeksKamera = (this.indeksKamera + 1) % this.kamera.length;
        await this.scanner.setCamera(this.kamera[this.indeksKamera].id);
        this.adaSenter = await this.scanner.hasFlash();
        this.simpanPilihan();
      },
      senter: async function () {
        if (!this.scanner || !this.adaSenter) { return; }
        await this.scanner.toggleFlash();
        this.senterNyala = this.scanner.isFlashOn();
      },
      kunciLayar: async function () {
        // Layar jangan mati selama memindai (Screen Wake Lock API, bila didukung).
        try {
          if ("wakeLock" in navigator && !this._wakeLock) {
            this._wakeLock = await navigator.wakeLock.request("screen");
            var self = this;
            this._wakeLock.addEventListener("release", function () { self._wakeLock = null; });
          }
        } catch (e) { /* tidak didukung */ }
      },

      // --- Umpan balik: bunyi dan getar ---------------------------------------------
      bunyi: function (status) {
        if (navigator.vibrate) {
          navigator.vibrate({ HIJAU: 80, KUNING: [80, 80, 80], MERAH: 500, GALAT: 500, MENUNGGU: [40, 60, 40] }[status] || 0);
        }
        if (!this.suara) { return; }
        try {
          this._audio = this._audio || new (window.AudioContext || window.webkitAudioContext)();
          var ctx = this._audio, osc = ctx.createOscillator(), g = ctx.createGain();
          osc.frequency.value = { HIJAU: 1320, KUNING: 760, MERAH: 220, GALAT: 220, MENUNGGU: 520 }[status] || 600;
          osc.type = status === "MERAH" || status === "GALAT" ? "square" : "sine";
          g.gain.value = 0.15;
          osc.connect(g); g.connect(ctx.destination);
          osc.start();
          osc.stop(ctx.currentTime + (status === "HIJAU" ? 0.12 : 0.35));
        } catch (e) { /* tanpa suara */ }
      },
      tampilkan: function (h) {
        var self = this;
        this.hasil = h;
        this.bunyi(h.status);
        clearTimeout(this._timerHasil);
        this._timerHasil = setTimeout(function () { self.hasil = null; }, h.status === "HIJAU" ? TAMPIL_HIJAU_MS : TAMPIL_LAIN_MS);
      },
      tutupHasil: function () { clearTimeout(this._timerHasil); this.hasil = null; },

      // --- Pindai -------------------------------------------------------------------
      terbaca: function (data) {
        if (!data || !this.titik || this.hasil || this.cari.buka) { return; }
        var t = Date.now();
        // Kunci QR yang sama selama 3 detik agar tidak terbaca berkali-kali.
        if (this._kunciQr[data] && t - this._kunciQr[data] < KUNCI_LOCK_MS) { return; }
        this._kunciQr[data] = t;
        this.proses({ qr: data, metode: "SCAN" });
      },
      proses: async function (isian) {
        // Kartu yang sama di titik yang sama masih tertahan di HP: jangan tambah antrean ganda.
        var tertahan = await this.cariDiAntrean(isian, this.titik.id);
        if (tertahan) {
          this.tampilkan({
            status: "MENUNGGU",
            judul: "Sudah tersimpan di HP",
            nama: tertahan.nama_cache || "",
            detail: "",
            pesan: "Pindaian kartu ini masih menunggu terkirim. Tidak perlu dipindai lagi.",
            bentrok: ""
          });
          return;
        }
        var item = {
          client_uuid: window.SIGAP.uuid(),
          titik_absen_id: this.titik.id,
          titik_nama: this.titik.nama,
          qr: isian.qr || "",
          metode: isian.metode,
          peserta_id: isian.peserta_id || null,
          dipindai_pada: sekarangIso(),
          dibuat_ms: Date.now(),
          nama_pemindai: this.namaPemindai,
          perangkat_id: window.SIGAP.perangkatId(),
          offline: false
        };
        var dariCache = isian.nama ? isian : await this.cariDiCache(item.qr);
        item.nama_cache = dariCache ? dariCache.nama : "";
        await this.simpanAntrean(item);
        this.tambahRiwayat(item, "MENUNGGU", item.nama_cache, "mengirim…");
        var jawab = await this.kirimSatu(item);
        if (jawab) {
          await this.hapusAntrean(item.client_uuid);
          this.terapkanJawaban(item, jawab, true);
          this.perbaruiRingkas();
        } else {
          item.offline = true;
          await this.simpanAntrean(item);
          this.tambahRiwayat(item, "MENUNGGU", item.nama_cache, "tersimpan di HP, akan dikirim otomatis");
          this.tampilkan({
            status: "MENUNGGU",
            judul: "Tersimpan di HP",
            nama: item.nama_cache || "",
            detail: dariCache ? dariCache.kontingen + " · " + (LABEL_TINGKAT[dariCache.tingkat] || "") : "",
            pesan: this.sesiHabis ? "Sesi habis. Masuk lagi; pindaian akan dikirim otomatis." : "Belum terkirim (sinyal). Akan dikirim otomatis.",
            bentrok: ""
          });
        }
      },
      kirimSatu: function (item) {
        var self = this;
        var kontrol = window.AbortController ? new AbortController() : null;
        var batas = setTimeout(function () { if (kontrol) { kontrol.abort(); } }, 8000);
        return fetch("/api/pindai", {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json", "X-CSRFToken": window.SIGAP.csrf(), "X-Requested-With": "XMLHttpRequest" },
          body: JSON.stringify(item),
          signal: kontrol ? kontrol.signal : undefined
        }).then(function (r) {
          clearTimeout(batas);
          if (r.status === 401) { self.sesiHabis = true; return null; }
          if (r.status === 403) { return null; } // CSRF kedaluwarsa: tetap di antrean
          if (r.status === 400) { return r.json().then(function (d) { return { status: "GALAT", kode: d.galat, pesan: d.pesan }; }); }
          if (!r.ok) { return null; }
          self.daring = true;
          self.sesiHabis = false;
          return r.json();
        }).catch(function () { clearTimeout(batas); self.daring = false; return null; });
      },
      terapkanJawaban: function (item, j, tampil) {
        var p = j.peserta || {};
        var judul = { HIJAU: "Berhasil", KUNING: "Sudah tercatat", MERAH: "Ditolak", GALAT: "Gagal" }[j.status] || j.status;
        var ket = j.status === "HIJAU" ? (p.kode_kontingen || "") + " · " + (j.tercatat_pada || jamSekarang()) : j.pesan;
        if (item.offline && j.status === "HIJAU") { ket += " (terkirim dari antrean)"; }
        this.tambahRiwayat(item, j.status, p.nama || item.nama_cache, ket);
        if (tampil) {
          this.tampilkan({
            status: j.status,
            judul: judul,
            nama: p.nama || "",
            detail: p.nama ? p.kontingen + " · " + (LABEL_TINGKAT[p.tingkat] || p.tingkat || "") + " · " + p.peran : "",
            pesan: j.status === "HIJAU" ? "" : j.pesan,
            bentrok: j.info_bentrok || ""
          });
        }
      },
      tambahRiwayat: function (item, status, nama, ket) {
        var ada = this.riwayat.find(function (r) { return r.client_uuid === item.client_uuid; });
        var data = { client_uuid: item.client_uuid, status: status, nama: nama, keterangan: ket, jam: ada ? ada.jam : jamSekarang() };
        if (ada) { Object.assign(ada, data); } else { this.riwayat.unshift(data); }
        this.riwayat = this.riwayat.slice(0, 10);
      },

      // --- Antrean IndexedDB ------------------------------------------------------------
      simpanAntrean: function (item) {
        if (!tokoAntrean) { return Promise.resolve(); }
        var self = this;
        return idb.set(item.client_uuid, item, tokoAntrean).then(function () { return self.hitungAntrean(); }).catch(function () {});
      },
      hapusAntrean: function (cu) {
        if (!tokoAntrean) { return Promise.resolve(); }
        var self = this;
        return idb.del(cu, tokoAntrean).then(function () { return self.hitungAntrean(); }).catch(function () {});
      },
      cariDiAntrean: function (isian, titikId) {
        if (!tokoAntrean) { return Promise.resolve(null); }
        return idb.values(tokoAntrean).then(function (v) {
          return v.find(function (x) {
            if (!x.offline || x.titik_absen_id !== titikId) { return false; }
            return isian.peserta_id ? x.peserta_id === isian.peserta_id : (isian.qr && x.qr === isian.qr);
          }) || null;
        }).catch(function () { return null; });
      },
      hitungAntrean: function () {
        var self = this;
        if (!tokoAntrean) { return Promise.resolve(); }
        // Yang sedang dikirim (baru dibuat, belum gagal) tidak dihitung "menunggu": spanduk kuning
        // hanya muncul untuk pindaian yang benar-benar tertahan di HP.
        var batas = Date.now() - BATAS_SEDANG_KIRIM_MS;
        return idb.values(tokoAntrean).then(function (v) {
          self.menunggu = v.filter(function (x) { return x.offline || (x.dibuat_ms || 0) < batas; }).length;
        }).catch(function () {});
      },
      kirimAntrean: async function (paksa) {
        if (this._mengirim || !tokoAntrean) { return; }
        if (!navigator.onLine && !paksa) { return; }
        this._mengirim = true;
        try {
          var semua = await idb.values(tokoAntrean);
          // Yang gagal terkirim, atau yang tertinggal lebih dari 30 detik (misalnya halaman tertutup saat mengirim).
          var batasLama = Date.now() - 30000;
          var siap = semua.filter(function (x) { return x.offline || (x.dibuat_ms || 0) < batasLama; }).slice(0, BATAS_BATCH);
          if (!siap.length) { return; }
          var r = await fetch("/api/pindai/batch", {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json", "X-CSRFToken": window.SIGAP.csrf(), "X-Requested-With": "XMLHttpRequest" },
            body: JSON.stringify({ pindaian: siap })
          });
          if (r.status === 401) { this.sesiHabis = true; return; }
          if (!r.ok) { return; }
          this.sesiHabis = false;
          this.daring = true;
          var d = await r.json();
          for (var i = 0; i < d.hasil.length; i++) {
            var j = d.hasil[i];
            var item = siap.find(function (x) { return x.client_uuid === j.client_uuid; });
            if (!item) { continue; }
            await idb.del(item.client_uuid, tokoAntrean);
            this.terapkanJawaban(item, j, false);
          }
          await this.hitungAntrean();
          this.perbaruiRingkas();
        } catch (e) {
          this.daring = false;
        } finally {
          this._mengirim = false;
        }
      },

      // --- Cari manual ---------------------------------------------------------------------
      bukaCari: function () {
        var self = this;
        this.cari = { buka: true, q: "", hasil: [], memuat: false };
        this.$nextTick(function () { self.$refs.isianCari.focus(); });
      },
      jalankanCari: function () {
        var self = this, q = this.cari.q.trim();
        if (q.length < 2) { this.cari.hasil = []; return; }
        this.cari.memuat = true;
        fetch("/api/cari-peserta/?q=" + encodeURIComponent(q) + "&titik=" + this.titik.id, { credentials: "same-origin" })
          .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
          .then(function (d) { self.cari.hasil = d.hasil; })
          .catch(function () {
            // Offline: cari di cache nama.
            var kecil = q.toLowerCase(), kode = q.toUpperCase().replace(/[\s-]/g, "");
            self.cari.hasil = (self._cache || []).filter(function (p) {
              return p.nama.toLowerCase().indexOf(kecil) !== -1 || (kode.length === 8 && p.k === kode.slice(0, 4) + "-" + kode.slice(4));
            }).slice(0, 20);
          })
          .finally(function () { self.cari.memuat = false; });
      },
      pilihManual: function (o) {
        var teks = "Catat kehadiran " + o.nama + (o.kontingen ? " (" + o.kontingen + ")" : "") + " secara manual?";
        if (!window.confirm(teks)) { return; }
        this.cari.buka = false;
        this.proses({ metode: "MANUAL", peserta_id: o.id, nama: o.nama, kontingen: o.kontingen, tingkat: o.tingkat });
      }
    };
  });
});
