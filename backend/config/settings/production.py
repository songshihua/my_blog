"""Production settings with fail-closed secret and HTTPS validation."""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False

# Public production traffic must never be able to trigger metered or remote
# ingestion. Add a separately authenticated job/admin flow before changing this.
RADAR_BROWSER_SYNC_ENABLED = False
RADAR_BRIEF_GENERATION_ENABLED = False
NOTE_BROWSER_IMPORT_ENABLED = False


def production_value(name: str, *, minimum_length: int = 1) -> str:
    value = os.getenv(name, "").strip()
    if (
        len(value) < minimum_length
        or value.startswith("replace-with-")
        or value in {"unsafe-development-key-change-me", "blog.example.com"}
    ):
        raise ImproperlyConfigured(f"Set a valid {name} for production")
    return value


SECRET_KEY = production_value("DJANGO_SECRET_KEY", minimum_length=50)
if len(set(SECRET_KEY)) < 8:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY does not have enough character variety")
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")  # noqa: F405
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must be set in production")
if not any(
    host not in {"localhost", "127.0.0.1", "backend", "blog.example.com"}
    for host in ALLOWED_HOSTS
):
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must include the real production hostname"
    )

CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")  # noqa: F405
if not CSRF_TRUSTED_ORIGINS or any(
    not origin.startswith("https://") for origin in CSRF_TRUSTED_ORIGINS
):
    raise ImproperlyConfigured(
        "DJANGO_CSRF_TRUSTED_ORIGINS must contain production HTTPS origins"
    )

database_password = production_value("MYSQL_PASSWORD", minimum_length=20)
if len(set(database_password)) < 6:
    raise ImproperlyConfigured("MYSQL_PASSWORD does not have enough character variety")
database_port = production_value("MYSQL_PORT")
if not database_port.isdigit():
    raise ImproperlyConfigured("MYSQL_PORT must be numeric")

DATABASES["default"].update(  # noqa: F405
    {
        "NAME": production_value("MYSQL_DATABASE"),
        "USER": production_value("MYSQL_USER"),
        "PASSWORD": database_password,
        "HOST": production_value("MYSQL_HOST"),
        "PORT": database_port,
    }
)

SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)  # noqa: F405
SESSION_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", True)  # noqa: F405
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(  # noqa: F405
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", True
)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)  # noqa: F405
if not SECURE_SSL_REDIRECT or not SESSION_COOKIE_SECURE or SECURE_HSTS_SECONDS <= 0:
    raise ImproperlyConfigured(
        "Production requires SSL redirect, secure cookies, and a positive HSTS duration"
    )

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
