"""Settings shared by development, test, and production environments."""

from __future__ import annotations

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPOSITORY_DIR = Path(os.getenv("PROJECT_ROOT", str(BACKEND_DIR.parent))).resolve()

# Direct host development reads the repository-local .env. Container and CI
# variables already present in the process take precedence over the file.
load_dotenv(REPOSITORY_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    """Read a conventional boolean value from the environment."""

    return os.getenv(name, str(default)).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def env_list(name: str, default: str = "") -> list[str]:
    """Read a comma-separated environment variable as a clean list."""

    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


def env_int(name: str, default: int, minimum: int = 1, maximum: int = 100) -> int:
    """Read and clamp an integer so remote-provider settings stay bounded."""

    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(value, maximum))


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ImproperlyConfigured(f"Required environment variable is missing: {name}")
    return value


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-development-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "django_filters",
    "rest_framework",
    "drf_spectacular",
    "apps.core",
    "apps.portfolio",
    "apps.blog",
    "apps.radar",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("MYSQL_DATABASE", "song_blog"),
        "USER": os.getenv("MYSQL_USER", "song_blog_app"),
        "PASSWORD": os.getenv("MYSQL_PASSWORD", "song_blog_dev_password"),
        "HOST": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "PORT": os.getenv("MYSQL_PORT", "3306"),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "charset": "utf8mb4",
            "isolation_level": "read committed",
            "connect_timeout": 10,
        },
        # Tests must never reuse the development or production database.
        "TEST": {"NAME": os.getenv("MYSQL_TEST_DATABASE", "song_blog_test")},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = REPOSITORY_DIR / "data" / "static"
MEDIA_URL = "/media/"
MEDIA_ROOT = REPOSITORY_DIR / "data" / "media"

# Original note documents are private application data. They deliberately live
# outside MEDIA_ROOT and can only be downloaded through the bounded API action.
NOTE_UPLOAD_ROOT = Path(
    os.getenv("NOTE_UPLOAD_ROOT", str(REPOSITORY_DIR / "data" / "notes"))
).resolve()
NOTE_UPLOAD_MAX_BYTES = env_int(
    "NOTE_UPLOAD_MAX_BYTES",
    8 * 1024 * 1024,
    minimum=1024,
    maximum=10 * 1024 * 1024,
)
NOTE_IMAGE_UPLOAD_MAX_BYTES = env_int(
    "NOTE_IMAGE_UPLOAD_MAX_BYTES",
    5 * 1024 * 1024,
    minimum=1024,
    maximum=10 * 1024 * 1024,
)
NOTE_BROWSER_IMPORT_ENABLED = False
DATA_UPLOAD_MAX_MEMORY_SIZE = max(
    NOTE_UPLOAD_MAX_BYTES,
    NOTE_IMAGE_UPLOAD_MAX_BYTES,
) + (512 * 1024)
FILE_UPLOAD_MAX_MEMORY_SIZE = max(
    NOTE_UPLOAD_MAX_BYTES,
    NOTE_IMAGE_UPLOAD_MAX_BYTES,
)
DATA_UPLOAD_MAX_NUMBER_FILES = 1

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAdminUser"],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.DefaultPagination",
    "PAGE_SIZE": 12,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SS·LAB API",
    "DESCRIPTION": "Read-only public API for the SS·LAB portfolio, notes, and AI radar.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

CORS_ALLOWED_ORIGINS = env_list("DJANGO_CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = False

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", False)
SESSION_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", False)
CSRF_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", False)
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", False
)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        }
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"}
    },
    "root": {"handlers": ["console"], "level": os.getenv("DJANGO_LOG_LEVEL", "INFO")},
}

# External integrations are invoked only by backend management commands. Tokens
# must never be exposed through NEXT_PUBLIC_* variables or serialized API output.
EXTERNAL_HTTP_USER_AGENT = os.getenv(
    "EXTERNAL_HTTP_USER_AGENT", "SS-LAB-Radar/1.0 (+https://github.com/songshihua)"
)
EXTERNAL_HTTP_TIMEOUT_SECONDS = env_int(
    "EXTERNAL_HTTP_TIMEOUT_SECONDS", 30, minimum=5, maximum=180
)
RADAR_SYNC_LIMIT = env_int("RADAR_SYNC_LIMIT", 20, minimum=1, maximum=100)
RADAR_BROWSER_SYNC_ENABLED = False
RADAR_BROWSER_SYNC_COOLDOWN_SECONDS = env_int(
    "RADAR_BROWSER_SYNC_COOLDOWN_SECONDS", 30, minimum=5, maximum=3600
)
RADAR_BRIEF_GENERATION_ENABLED = False
RADAR_BRIEF_ITEM_LIMIT = env_int("RADAR_BRIEF_ITEM_LIMIT", 20, minimum=3, maximum=50)
RADAR_BRIEF_CACHE_SECONDS = env_int(
    "RADAR_BRIEF_CACHE_SECONDS", 900, minimum=60, maximum=86400
)

ARXIV_SEARCH_QUERY = os.getenv("ARXIV_SEARCH_QUERY", "").strip()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
GITHUB_API_VERSION = os.getenv("GITHUB_API_VERSION", "2026-03-10").strip()
GITHUB_DISCOVERY_QUERY = os.getenv("GITHUB_DISCOVERY_QUERY", "llm").strip()
GITHUB_DISCOVERY_LOOKBACK_DAYS = env_int(
    "GITHUB_DISCOVERY_LOOKBACK_DAYS", 30, minimum=1, maximum=365
)
GITHUB_DISCOVERY_MIN_STARS = env_int(
    "GITHUB_DISCOVERY_MIN_STARS", 20, minimum=0, maximum=1_000_000
)
GITHUB_DISCOVERY_SORT = os.getenv("GITHUB_DISCOVERY_SORT", "stars").strip().lower()

HUGGINGFACE_AUTHOR = os.getenv("HUGGINGFACE_AUTHOR", "").strip()
HUGGINGFACE_SEARCH = os.getenv("HUGGINGFACE_SEARCH", "").strip()
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN", "").strip()
HUGGINGFACE_INCLUDE_DATASETS = env_bool("HUGGINGFACE_INCLUDE_DATASETS", True)

LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4-pro").strip()
LLM_FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "deepseek-v4-flash").strip()
LLM_LOOKBACK_DAYS = env_int("LLM_LOOKBACK_DAYS", 7, minimum=1, maximum=30)
LLM_REASONING_EFFORT = os.getenv("LLM_REASONING_EFFORT", "low").strip()
LLM_VERIFY_SOURCE_URLS = env_bool("LLM_VERIFY_SOURCE_URLS", True)
AI_RADAR_KEYWORDS = env_list(
    "AI_RADAR_KEYWORDS",
    "speculative decoding,KV Cache,LLM serving,inference optimization,long context",
)
AI_RADAR_ALLOWED_DOMAINS = env_list(
    "AI_RADAR_ALLOWED_DOMAINS",
    (
        "arxiv.org,openreview.net,huggingface.co,github.com,pytorch.org,nvidia.com,"
        "research.google,deepmind.google,ai.meta.com,microsoft.com,openai.com,"
        "anthropic.com"
    ),
)
