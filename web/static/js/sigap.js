/* SIGAP JUMBARA: skrip umum semua halaman.
 * - id perangkat (UUID acak sekali per browser) dan nama pelaku per akun, dikirim lewat cookie
 * - ingatan menu/rute terakhir per akun per perangkat
 * - jam berakhir sesi dan peringatan 5 menit sebelum habis
 * Semua akses localStorage dibungkus try/catch (mode privat bisa melempar galat).
 */
(function () {
  "use strict";

  var simpan = {
    ambil: function (k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } },
    tulis: function (k, v) { try { window.localStorage.setItem(k, v); return true; } catch (e) { return false; } },
    hapus: function (k) { try { window.localStorage.removeItem(k); } catch (e) { /* abaikan */ } },
    json: function (k, bawaan) { try { var v = window.localStorage.getItem(k); return v ? JSON.parse(v) : bawaan; } catch (e) { return bawaan; } },
    tulisJson: function (k, v) { try { window.localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* abaikan */ } }
  };

  function uuid() {
    if (window.crypto && window.crypto.randomUUID) { return window.crypto.randomUUID(); }
    var b = new Uint8Array(16);
    window.crypto.getRandomValues(b);
    b[6] = (b[6] & 0x0f) | 0x40; b[8] = (b[8] & 0x3f) | 0x80;
    var h = Array.prototype.map.call(b, function (x) { return ("0" + x.toString(16)).slice(-2); }).join("");
    return h.slice(0, 8) + "-" + h.slice(8, 12) + "-" + h.slice(12, 16) + "-" + h.slice(16, 20) + "-" + h.slice(20);
  }

  function setCookie(nama, nilai) {
    var aman = location.protocol === "https:" ? "; Secure" : "";
    document.cookie = nama + "=" + encodeURIComponent(nilai) + "; Path=/; Max-Age=31536000; SameSite=Lax" + aman;
  }

  function hapusCookie(nama) { document.cookie = nama + "=; Path=/; Max-Age=0; SameSite=Lax"; }

  // --- id perangkat ---------------------------------------------------------
  var perangkat = simpan.ambil("sigap:perangkat_id");
  if (!perangkat) { perangkat = uuid(); simpan.tulis("sigap:perangkat_id", perangkat); }
  setCookie("sigap_perangkat", perangkat);

  var body = document.body;
  var username = body ? body.getAttribute("data-username") : "";
  var peran = body ? body.getAttribute("data-peran") : "";
  var kunciIngatan = username ? "sigap:" + username + ":ingatan" : null;
  var kunciNama = username ? "sigap:" + username + ":nama" : null;

  function namaPelaku() { return kunciNama ? (simpan.ambil(kunciNama) || "") : ""; }

  function tampilkanNama() {
    var n = namaPelaku();
    document.querySelectorAll("[data-nama-pelaku-tampil]").forEach(function (el) { el.textContent = n ? " · " + n : ""; });
  }

  function aturNama(nama) {
    nama = (nama || "").replace(/\s+/g, " ").trim().slice(0, 60);
    if (!nama || !kunciNama) { return false; }
    simpan.tulis(kunciNama, nama);
    setCookie("sigap_nama", nama);
    tampilkanNama();
    return true;
  }

  if (username) {
    var n = namaPelaku();
    if (n) { setCookie("sigap_nama", n); } else { hapusCookie("sigap_nama"); }
  }

  // --- ingatan menu terakhir ------------------------------------------------
  function ingatan() { return kunciIngatan ? simpan.json(kunciIngatan, {}) : {}; }
  function simpanIngatan(data) { if (kunciIngatan) { simpan.tulisJson(kunciIngatan, data); } }

  if (username && body && body.hasAttribute("data-ingat-rute")) {
    var ing = ingatan();
    ing.rute_terakhir = location.pathname + location.search;
    simpanIngatan(ing);
  }

  window.SIGAP = {
    simpan: simpan,
    uuid: uuid,
    perangkatId: function () { return perangkat; },
    namaPelaku: namaPelaku,
    aturNama: aturNama,
    ingatan: ingatan,
    simpanIngatan: simpanIngatan,
    username: username,
    peran: peran,
    lupakanPerangkat: function () {
      try {
        var hapusKunci = [];
        for (var i = 0; i < localStorage.length; i++) {
          var k = localStorage.key(i);
          if (k && k.indexOf("sigap:") === 0 && k !== "sigap:perangkat_id") { hapusKunci.push(k); }
        }
        hapusKunci.forEach(function (k) { localStorage.removeItem(k); });
      } catch (e) { /* abaikan */ }
      hapusCookie("sigap_nama");
    },
    // Filter tabel: dibaca saat halaman dimuat, ditulis setiap kali berubah.
    filter: function (halaman) {
      var ing = ingatan();
      return (ing.filter && ing.filter[halaman]) || null;
    },
    simpanFilter: function (halaman, query) {
      var ing = ingatan();
      ing.filter = ing.filter || {};
      ing.filter[halaman] = query;
      simpanIngatan(ing);
    },
    csrf: function () {
      var m = document.cookie.match(/(?:^|;\s*)sigap_csrf=([^;]+)/);
      if (m) { return decodeURIComponent(m[1]); }
      var el = document.querySelector("input[name=csrfmiddlewaretoken]");
      return el ? el.value : "";
    }
  };

  // --- sesi: jam berakhir dan peringatan ------------------------------------
  document.addEventListener("DOMContentLoaded", function () {
    tampilkanNama();
    document.querySelectorAll("[data-nama-pelaku]").forEach(function (el) { el.textContent = namaPelaku() || "(belum diisi)"; });
    document.querySelectorAll("[data-ganti-nama]").forEach(function (b) {
      b.addEventListener("click", function () {
        var baru = window.prompt("Nama pemakai perangkat ini (dicatat di log):", namaPelaku());
        if (baru !== null && aturNama(baru)) { location.reload(); }
      });
    });
    document.querySelectorAll("[data-lupakan-perangkat]").forEach(function (b) {
      b.addEventListener("click", function () {
        if (window.confirm("Hapus semua ingatan di perangkat ini (nama, menu terakhir, filter)?")) {
          window.SIGAP.lupakanPerangkat();
          location.href = "/masuk/lanjut/";
        }
      });
    });
    var sisaAwal = body ? parseInt(body.getAttribute("data-sesi-sisa") || "0", 10) : 0;
    if (!sisaAwal) { return; }
    var akhir = Date.now() / 1000 + sisaAwal;
    var teksJam = body.getAttribute("data-sesi-jam") || "";
    document.querySelectorAll("[data-jam-sesi]").forEach(function (el) { el.textContent = teksJam; });
    var kotak = document.getElementById("peringatan-sesi");
    function periksa() {
      var sisa = akhir - Date.now() / 1000;
      if (sisa <= 0) {
        kotak.textContent = "Sesi sudah habis. Silakan masuk lagi.";
        kotak.classList.remove("hidden");
        return;
      }
      if (sisa <= 300) {
        var menit = Math.ceil(sisa / 60);
        kotak.textContent = "Sesi akan berakhir dalam " + menit + " menit (pukul " + teksJam + "). Simpan pekerjaan Anda, lalu masuk lagi.";
        kotak.classList.remove("hidden");
      }
    }
    periksa();
    setInterval(periksa, 20000);
  });

  // Halaman rekap: muat ulang setiap N detik (data-segar) sambil menjaga posisi gulir.
  document.addEventListener("DOMContentLoaded", function () {
    var detik = body ? parseInt(body.getAttribute("data-segar") || "0", 10) : 0;
    var kunci = "sigap:gulir:" + location.pathname + location.search;
    try {
      var y = sessionStorage.getItem(kunci);
      if (y) { window.scrollTo(0, parseInt(y, 10)); sessionStorage.removeItem(kunci); }
    } catch (e) { /* abaikan */ }
    if (!detik) { return; }
    setInterval(function () {
      var aktif = document.activeElement;
      var sedangMengetik = aktif && /INPUT|TEXTAREA|SELECT/.test(aktif.tagName);
      if (document.visibilityState !== "visible" || sedangMengetik) { return; }
      try { sessionStorage.setItem(kunci, String(window.scrollY)); } catch (e) { /* abaikan */ }
      location.reload();
    }, detik * 1000);
  });

  // Saat keluar, simpan rute terakhir tetap ada (sengaja), tapi hapus cookie nama.
  document.addEventListener("submit", function (e) {
    if (e.target && e.target.hasAttribute && e.target.hasAttribute("data-form-keluar")) { hapusCookie("sigap_nama"); }
  });
})();
