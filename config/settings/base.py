import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ── Django Core ────────────────────────────────────────────────────────

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-key-change-in-production")
DEBUG = False
ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "channels",
    "rest_framework",
    "apps.core.apps.CoreConfig",
    "apps.jobs.apps.JobsConfig",
    "apps.dashboard.apps.DashboardConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "apps" / "dashboard" / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Email ─────────────────────────────────────────────────────────────

EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASS = os.getenv("EMAIL_PASS", "")
EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "465"))

# ── AI (LLM cover letter generation) ──────────────────────────────

AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")
AI_API_BASE_URL = os.getenv("AI_API_BASE_URL", "https://api.openai.com/v1")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")

# ── Resume ────────────────────────────────────────────────────────────

RESUME_PATH = BASE_DIR / os.getenv("RESUME_PATH", "resume/Your_Resume.pdf")

# ── CV Engine (microservice) ────────────────────────────────────────

CV_ENGINE_BASE_URL = os.getenv("CV_ENGINE_BASE_URL", "http://127.0.0.1:8001")
CV_ENGINE_SERVICE_KEY = os.getenv("CV_ENGINE_SERVICE_KEY", "")

# ── Cover Letter Engine (microservice) ─────────────────────────────

COVER_LETTER_ENGINE_BASE_URL = os.getenv("COVER_LETTER_ENGINE_BASE_URL", "http://127.0.0.1:8002")
COVER_LETTER_ENGINE_SERVICE_KEY = os.getenv(
    "COVER_LETTER_ENGINE_SERVICE_KEY", "cover-letter-engine-dev-key"
)

# ── Job Matching Thresholds ──────────────────────────────────────────

MATCH_THRESHOLD_APPLY = 65
MATCH_THRESHOLD_TRACK = 50
MIN_SALARY = int(os.getenv("MIN_SALARY", "18000"))
MIN_PROJECT_MATCH = 1
MAX_SKILL_GAP_PCT = 40
MAX_SALARY_GAP_PCT = 50
MAX_SALARY = int(os.getenv("MAX_SALARY", "400000"))
MIN_EXPERIENCE = 0
MAX_EXPERIENCE = 15
MAX_LOCATION_DISTANCE_KM = 500

# ── Fetcher Config ────────────────────────────────────────────────────

FEED_BASE_URL = "https://rssjobs.app/feeds"
FETCH_INTERVAL_MINUTES = int(os.getenv("FETCH_INTERVAL_MINUTES", "60"))

# ── Data Lake + Warehouse (local-only) ────────────────────────────────

DATA_LAKE_DIR = os.path.join(BASE_DIR, "data_lake")
WAREHOUSE_DB_PATH = os.path.join(BASE_DIR, "warehouse", "jobbloot.duckdb")

# ── Dashboard ─────────────────────────────────────────────────────────

DASHBOARD_PAGE_SIZE = 50
DASHBOARD_STATS_DAYS = 14
DASHBOARD_MIN_SCORE_WEB_APPLY = 65
DASHBOARD_MIN_SCORE_TRACK = 40
