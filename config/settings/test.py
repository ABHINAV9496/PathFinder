from config.settings.base import *  # noqa: F401, F403

DEBUG = True

SECRET_KEY = "test-secret-key-not-for-production"

ALLOWED_HOSTS = ["*"]

# ── Database (fast in-memory for tests) ───────────────────────────────

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# ── Security (all off for tests) ──────────────────────────────────────

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# ── Password hashing (fast for tests) ─────────────────────────────────

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# ── Email (no-op backend) ─────────────────────────────────────────────

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# ── Data lake (off by default; lake/warehouse tests override to a tmp dir)

DATA_LAKE_DIR = None

# ── Logging (quiet during tests) ──────────────────────────────────────

LOGGING = {}
