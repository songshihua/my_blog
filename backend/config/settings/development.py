"""Local development settings."""

from .base import *  # noqa: F403

DEBUG = True
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# The public API is read-only and does not use browser credentials.
CORS_ALLOWED_ORIGINS = env_list(  # noqa: F405
    "DJANGO_CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)

# Browser-triggered ingestion is a local-development convenience. The API also
# verifies the request Origin and loopback address before making network calls.
RADAR_BROWSER_SYNC_ENABLED = env_bool("RADAR_BROWSER_SYNC_ENABLED", True)  # noqa: F405

# Personal note authoring is available only from the trusted local frontend.
NOTE_BROWSER_IMPORT_ENABLED = env_bool(  # noqa: F405
    "NOTE_BROWSER_IMPORT_ENABLED", True
)
