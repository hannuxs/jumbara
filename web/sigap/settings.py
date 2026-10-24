"""Pengaturan Django untuk SIGAP JUMBARA.

Semua nilai yang berbeda antara laptop pengembangan dan server produksi dibaca dari
`web\\.env` (lihat `.env.example`). Jangan menulis rahasia di file ini.
"""

import sys
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

# --- Dasar -------------------------------------------------------------------
DEBUG = env.bool("DJANGO_DEBUG", default=False)
SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
SIGAP_URL = env("SIGAP_URL", default="https://localhost:8585").rstrip("/")
# Port jalankan.bat (pengembangan HTTPS / Waitress produksi di belakang Caddy).
SIGAP_PORT = env.int("SIGAP_PORT", default=8585)

# Mode tes (pytest) mematikan hal yang tidak perlu saat tes, misalnya manifest statis.
SEDANG_TES = env.bool("SIGAP_SEDANG_TES", default=False) or "pytest" in sys.modules

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    # WhiteNoise juga melayani /static/ saat runserver (cache dikendalikan WHITENOISE_MAX_AGE).
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.admin",
    "apps.inti",
    "apps.akun",
    "apps.kontingen",
    "apps.biodata",
    "apps.kartu",
    "apps.absensi",
    "apps.anjangsana",
    "apps.penilaian",
    "apps.piagam",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "apps.akun.middleware.SesiMutlakMiddleware",
    "apps.inti.middleware.PelakuMiddleware",
    "apps.inti.middleware.PerawatanMiddleware",
    "apps.inti.middleware.HeaderKeamananMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "sigap.urls"
WSGI_APPLICATION = "sigap.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.inti.context_processors.sigap",
            ],
        },
    },
]

# --- Database (MariaDB 10.5+) -------------------------------------------------
# TIME_ZONE database = Asia/Makassar: jam di database tersimpan dalam WITA dan Django
# tidak memakai CONVERT_TZ (tabel zona waktu MariaDB di Windows biasanya kosong).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("DB_NAME", default="sigap_jumbara"),
        "USER": env("DB_USER", default="sigap"),
        "PASSWORD": env("DB_PASSWORD", default=""),
        "HOST": env("DB_HOST", default="127.0.0.1"),
        "PORT": env("DB_PORT", default="3306"),
        "TIME_ZONE": "Asia/Makassar",
        "CONN_MAX_AGE": env.int("DB_CONN_MAX_AGE", default=60),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": (
                "SET time_zone='+08:00', "
                "sql_mode='STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'"
            ),
        },
        "TEST": {
            "NAME": env("DB_TEST_NAME", default="sigap_jumbara_test"),
            "CHARSET": "utf8mb4",
            "COLLATION": "utf8mb4_unicode_ci",
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Cache (database, aman dibagi antarthread Waitress untuk rate limit) -------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "sigap_cache",
        "TIMEOUT": 600,
    }
}
RATELIMIT_USE_CACHE = "default"
RATELIMIT_VIEW = "apps.inti.views.terlalu_banyak"
# Di balik Apache/Cloudflare, IP asli ada di X-Forwarded-For (lihat apps.inti.utils.ip_klien).
RATELIMIT_IP_META_KEY = "apps.inti.utils.ip_klien_meta"

# --- Akun dan sesi -------------------------------------------------------------
AUTH_USER_MODEL = "akun.Pengguna"
LOGIN_URL = "akun:masuk"
LOGIN_REDIRECT_URL = "akun:lanjut"
LOGOUT_REDIRECT_URL = "akun:masuk"

SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 2 * 60 * 60  # 2 jam; batas mutlak dijaga SesiMutlakMiddleware
SESSION_SAVE_EVERY_REQUEST = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_NAME = "sigap_sesi"
CSRF_COOKIE_NAME = "sigap_csrf"
CSRF_FAILURE_VIEW = "apps.inti.views.csrf_gagal"
SIGAP_SESI_MENIT = env.int("SIGAP_SESI_MENIT", default=120)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

if SEDANG_TES:
    # Hash cepat khusus tes otomatis (tidak pernah dipakai di produksi).
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# --- Bahasa dan waktu ----------------------------------------------------------
LANGUAGE_CODE = "id"
LANGUAGES = [("id", "Bahasa Indonesia")]
TIME_ZONE = "Asia/Makassar"
USE_I18N = True
USE_TZ = True
# Jangan aktifkan USE_THOUSAND_SEPARATOR: angka id di URL bisa ikut diberi titik.

# --- Statis dan file privat ----------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG or SEDANG_TES
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}
# Pengembangan: 0 agar browser tidak memakai JS/CSS lama (nama file belum ber-hash).
WHITENOISE_MAX_AGE = 0 if DEBUG else 60 * 60 * 24 * 30

# Folder privat (foto, cadangan sementara). WAJIB di luar static dan di luar DocumentRoot Apache.
SIGAP_FOLDER_PRIVAT = Path(env("SIGAP_FOLDER_PRIVAT", default=str(BASE_DIR / "privat")))
SIGAP_FOLDER_CADANGAN = Path(env("SIGAP_FOLDER_CADANGAN", default=str(BASE_DIR / "privat" / "cadangan")))
SIGAP_MYSQLDUMP_PATH = env("SIGAP_MYSQLDUMP_PATH", default=r"C:\xampp\mysql\bin\mysqldump.exe")
SIGAP_CADANGAN_SIMPAN_HARI = env.int("SIGAP_CADANGAN_SIMPAN_HARI", default=14)

# Kunci enkripsi NIK (Fernet) dan kunci HMAC untuk cek NIK dobel. JANGAN hilang: tanpa kunci
# ini NIK di database tidak bisa dibaca lagi. Simpan salinannya di tempat aman.
SIGAP_KUNCI_NIK = env.list("SIGAP_KUNCI_NIK")
SIGAP_KUNCI_HASH_NIK = env("SIGAP_KUNCI_HASH_NIK")

FILE_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
FILE_UPLOAD_PERMISSIONS = None

# --- Keamanan (aktif penuh di produksi) ---------------------------------------
SIGAP_HTTPS = env.bool("SIGAP_HTTPS", default=not DEBUG)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = env.bool("USE_X_FORWARDED_HOST", default=False)
SESSION_COOKIE_SECURE = SIGAP_HTTPS
CSRF_COOKIE_SECURE = SIGAP_HTTPS
# Di balik Cloudflare Tunnel, pengalihan ke HTTPS sudah dilakukan Cloudflare; aktifkan hanya
# jika yakin tidak terjadi putaran pengalihan.
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
# COOP dikirim HeaderKeamananMiddleware hanya lewat HTTPS (di HTTP biasa browser memberi peringatan).
SECURE_CROSS_ORIGIN_OPENER_POLICY = None
SILENCED_SYSTEM_CHECKS = env.list("SILENCED_SYSTEM_CHECKS", default=[])

# --- Log berkas ------------------------------------------------------------------
FOLDER_LOG = Path(env("SIGAP_FOLDER_LOG", default=str(BASE_DIR / "logs")))
FOLDER_LOG.mkdir(parents=True, exist_ok=True)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"biasa": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {
        "konsol": {"class": "logging.StreamHandler", "formatter": "biasa"},
        "berkas": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(FOLDER_LOG / "django.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
            "formatter": "biasa",
            "delay": True,
        },
    },
    "root": {"handlers": ["konsol", "berkas"], "level": "WARNING"},
    "loggers": {
        "sigap": {"handlers": ["konsol", "berkas"], "level": "INFO", "propagate": False},
    },
}
