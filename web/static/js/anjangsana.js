/* Anjangsana publik (tanpa login). docs/17-ANJANGSANA.md
 *
 * Alur: pindai kartu sendiri -> konfirmasi 1 -> pindai QR kontingen tuan rumah -> konfirmasi 2
 * -> kunjungan tercatat -> review -> terima kasih. Identitas (tiket bertanda tangan dari server)
 * disimpan di HP ini 30 menit agar "Kunjungi kontingen lain" tidak perlu memindai kartu lagi.
 */
document.addEventListener("alpine:init", function () {
  "use strict";
  var KUNCI_IDENTITAS = "sigap-anjangsana-identitas";
  var KUNCI_QR_MS = 3000;

  function simpan(kunci, nilai) {
    try {
      if (nilai === null) { localStorage.removeItem(kunci); } else { localStorage.setItem(kunci, JSON.stringify(nilai)); }
    } catch (e) { /* penyimpanan tidak tersedia */ }
  }
  function baca(kunci) {
    try { return JSON.parse(localStorage.getItem(kunci) || "null"); } catch (e) { return null; }
  }

  window.Alpine.data("anjangsana", function () {
    return {
      tahap: "awal",
      identitas: null,       // {tiket, nama, kontingen, sampai}
      tuan: null,            // {tuan_rumah, tiket_tuan, peringatan}
      kunjungan: null,       // {tiket_kunjungan, tuan_rumah, aspek}
      nilai: { pengetahuan: 0, keterampilan: 0, sikap: 0 },
      komentar: "",
      ganti: false,
      galat: "",
      sibuk: false,
      kodeManual: "",
      tutup: false,
      // kamera
      scanner: null,
      kameraAktif: false,
      pesanKamera: "",
      _kunci: {},

      mulai: function () {
        this.tutup = this.$root.dataset.tutup === "1";
        var id = baca(KUNCI_IDENTITAS);
        if (id && id.sampai > Date.now()) { this.identitas = id; } else { simpan(KUNCI_IDENTITAS, null); }
        var self = this;
        document.addEventListener("visibilitychange", function () {
          if (document.hidden) { self.matikanKamera(); } else if (self.tahapKamera()) { self.nyalakanKamera(); }
        });
      },
      tahapKamera: function () { return this.tahap === "kartu" || this.tahap === "tuan"; },
      menitTersisa: function () {
        return this.identitas ? Math.max(1, Math.round((this.identitas.sampai - Date.now()) / 60000)) : 0;
      },

      ke: function (tahap) {
        this.galat = "";
        this.tahap = tahap;
        window.scrollTo(0, 0);
        if (this.tahapKamera()) { this.$nextTick(this.nyalakanKamera.bind(this)); } else { this.matikanKamera(); }
      },
      pindaiKartu: function () { this.kodeManual = ""; this.ke("kartu"); },
      lanjutIdentitas: function () {
        if (!this.identitas || this.identitas.sampai <= Date.now()) { this.lupakan(); this.pindaiKartu(); return; }
        this.ke("tuan");
      },
      lupakan: function () {
        this.identitas = null;
        simpan(KUNCI_IDENTITAS, null);
        this.ke("awal");
      },

      // --- Server ------------------------------------------------------------
      kirim: async function (alamat, data) {
        this.sibuk = true;
        this.galat = "";
        try {
          var r = await fetch("/anjangsana/api/" + alamat, {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json", "X-CSRFToken": window.SIGAP.csrf(), "X-Requested-With": "XMLHttpRequest" },
            body: JSON.stringify(data)
          });
          var j = null;
          try { j = await r.json(); } catch (e) { j = null; }
          if (!j) { return { ok: false, kode: "GALAT", pesan: r.status === 403 ? "Halaman kedaluwarsa. Muat ulang halaman." : "Server sedang bermasalah. Coba lagi." }; }
          if (j.kode === "TIDAK_BERLANGSUNG") { this.tutup = true; }
          if (j.kode === "TIKET_KEDALUWARSA" || j.kode === "TIKET_SALAH" || j.kode === "KARTU_NONAKTIF") {
            if (alamat !== "kartu") { this.identitas = null; simpan(KUNCI_IDENTITAS, null); }
          }
          return j;
        } catch (e) {
          return { ok: false, kode: "JARINGAN", pesan: "Tidak ada sinyal. Periksa internet lalu coba lagi." };
        } finally {
          this.sibuk = false;
        }
      },
      getar: function (ok) {
        if (navigator.vibrate) { try { navigator.vibrate(ok ? 80 : 400); } catch (e) { /* abaikan */ } }
      },

      terbaca: async function (teks) {
        if (this.sibuk) { return; }
        var kini = Date.now();
        if (this._kunci[teks] && kini - this._kunci[teks] < KUNCI_QR_MS) { return; }
        this._kunci[teks] = kini;
        if (this.tahap === "kartu") { await this.kirimKartu(teks); } else if (this.tahap === "tuan") { await this.kirimTuan(teks); }
      },
      kirimKartu: async function (teks) {
        var j = await this.kirim("kartu", { teks: teks });
        this.getar(j.ok);
        if (!j.ok) { this.galat = j.pesan; return; }
        this.identitas = { tiket: j.tiket, nama: j.nama, kontingen: j.kontingen, sampai: Date.now() + j.berlaku_menit * 60000 };
        this.ke("konfirmasi1");
      },
      kirimKodeManual: function () {
        var kode = this.kodeManual.trim();
        if (kode.replace(/[\s-]/g, "").length !== 8) { this.galat = "Kode kartu terdiri dari 8 huruf/angka, contoh K7Q2-M4XA."; return; }
        this.kirimKartu(kode);
      },
      setujuIdentitas: function () {
        simpan(KUNCI_IDENTITAS, this.identitas);
        this.ke("tuan");
      },
      kirimTuan: async function (teks) {
        var j = await this.kirim("tuan-rumah", { tiket: this.identitas.tiket, teks: teks });
        this.getar(j.ok);
        if (!j.ok) {
          this.galat = j.pesan;
          if (!this.identitas) { this.ke("awal"); this.galat = j.pesan; }
          return;
        }
        this.tuan = j;
        this.ganti = !!j.peringatan;
        this.ke("konfirmasi2");
      },
      setujuTuan: async function () {
        var j = await this.kirim("kunjungan", { tiket_tuan: this.tuan.tiket_tuan });
        if (!j.ok) {
          if (!this.identitas) { this.ke("awal"); }
          this.galat = j.pesan;
          return;
        }
        this.kunjungan = j;
        this.nilai = { pengetahuan: 0, keterampilan: 0, sikap: 0 };
        this.komentar = "";
        this.ke("review");
      },
      lengkap: function () { return this.nilai.pengetahuan && this.nilai.keterampilan && this.nilai.sikap; },
      kirimReview: async function () {
        if (!this.lengkap()) { this.galat = "Pilih nilai 1 sampai 5 untuk setiap aspek."; return; }
        var j = await this.kirim("review", { tiket_kunjungan: this.kunjungan.tiket_kunjungan, nilai: this.nilai, komentar: this.komentar, ganti: this.ganti });
        if (!j.ok) {
          if (j.kode === "SUDAH_ADA") {
            // Anggota lain baru saja mengirim: tampilkan peringatan, kirim lagi berarti mengganti.
            this.tuan.peringatan = j.pesan;
            this.ganti = true;
          }
          this.galat = j.pesan;
          return;
        }
        this.ke("selesai");
      },

      // --- Kamera -------------------------------------------------------------
      nyalakanKamera: async function () {
        var self = this;
        this.pesanKamera = "";
        if (!this.$refs.video) { return; }
        if (!window.QrScanner) { this.pesanKamera = "Pustaka pemindai tidak termuat. Muat ulang halaman."; return; }
        if (!window.isSecureContext) {
          this.pesanKamera = "Kamera hanya bisa dipakai lewat alamat https://. Ketik kode kartu di bawah.";
          return;
        }
        try {
          if (!this.scanner) {
            this.scanner = new window.QrScanner(this.$refs.video, function (r) { self.terbaca(r.data); }, {
              returnDetailedScanResult: true,
              highlightScanRegion: true,
              highlightCodeOutline: true,
              maxScansPerSecond: 6,
              preferredCamera: "environment"
            });
          }
          await this.scanner.start();
          this.kameraAktif = true;
        } catch (e) {
          this.kameraAktif = false;
          var nama = (e && (e.name || e)) + "";
          if (nama.indexOf("NotAllowed") !== -1 || nama.indexOf("permission") !== -1) {
            this.pesanKamera = "Izin kamera ditolak. Chrome: ketuk ikon gembok di samping alamat > Izin > Kamera > Izinkan. Safari iPhone: Pengaturan > Safari > Kamera > Izinkan. Lalu tekan Coba lagi.";
          } else if (nama.indexOf("NotFound") !== -1 || nama.indexOf("Camera not found") !== -1) {
            this.pesanKamera = "Kamera tidak ditemukan di perangkat ini.";
          } else {
            this.pesanKamera = "Kamera tidak bisa dinyalakan. Tutup aplikasi lain yang memakai kamera lalu Coba lagi.";
          }
        }
      },
      matikanKamera: function () {
        if (this.scanner) { this.scanner.stop(); }
        this.kameraAktif = false;
      }
    };
  });
});
