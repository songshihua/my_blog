"""Local development settings."""

from .base import *  # noqa: F403

DEBUG = True
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# The public API is read-only and does not use browser credentials.
CORS_ALLOWED_ORIGINS = env_list(  # noqa: F405
    "DJANGO_CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)
