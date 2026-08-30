"""Shared, bounded primitives for remote provider integrations."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol
from urllib.parse import urlsplit, urlunsplit

import httpx
from django.utils import timezone

CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class ProviderError(RuntimeError):
    """Safe provider failure whose message may be stored in an ingestion log."""


class ProviderNotConfigured(ProviderError):
    """The provider is disabled because a required non-public setting is missing."""


class ProviderResponseError(ProviderError):
    """The provider returned an unusable response."""


@dataclass(frozen=True, slots=True)
class ExternalRecord:
    external_id: str
    kind: str
    title: str
    original_url: str
    summary: str
    authors: list[str]
    published_at: datetime
    topics: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    ai_summary: dict[str, str] = field(default_factory=dict)
    relevance_score: Decimal = Decimal("0")
    project: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ProviderBatch:
    records: list[ExternalRecord]
    sync_state: dict[str, Any] = field(default_factory=dict)
    not_modified: bool = False


class RemoteProvider(Protocol):
    source_type: str

    def configuration_error(self) -> str | None: ...

    def fetch(self, limit: int) -> ProviderBatch: ...


def clean_text(value: object, max_length: int) -> str:
    """Normalize untrusted provider text and apply database field bounds."""

    if value is None:
        return ""
    normalized = CONTROL_CHARACTERS.sub("", str(value)).replace("\r\n", "\n").strip()
    return normalized[:max_length]


def clean_string_list(value: object, *, limit: int = 20, item_length: int = 100) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    cleaned: list[str] = []
    for item in value:
        text = clean_text(item, item_length)
        if text and text not in cleaned:
            cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return cleaned


def canonical_http_url(value: object, *, require_https: bool = True) -> str:
    """Return a credential-free HTTP(S) URL, or an empty string when invalid."""

    text = clean_text(value, 500)
    if not text:
        return ""
    try:
        parsed = urlsplit(text)
    except ValueError:
        return ""
    allowed_schemes = {"https"} if require_https else {"http", "https"}
    if parsed.scheme.lower() not in allowed_schemes or not parsed.hostname:
        return ""
    if parsed.username or parsed.password:
        return ""
    return urlunsplit(
        (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, parsed.query, "")
    )[:500]


def host_is_allowed(url: str, allowed_domains: list[str]) -> bool:
    try:
        hostname = (urlsplit(url).hostname or "").lower().rstrip(".")
    except ValueError:
        return False
    return any(
        hostname == domain.lower().rstrip(".")
        or hostname.endswith(f".{domain.lower().rstrip('.')}")
        for domain in allowed_domains
    )


def parse_timestamp(value: object, *, fallback: datetime | None = None) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        text = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ProviderResponseError("Provider returned an invalid timestamp.") from exc
    elif fallback is not None:
        parsed = fallback
    else:
        raise ProviderResponseError("Provider response is missing a timestamp.")
    if timezone.is_naive(parsed):
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def request_with_retries(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    provider_name: str,
    attempts: int = 3,
    **kwargs: Any,
) -> httpx.Response:
    """Perform a bounded retry loop without including credentials in errors."""

    last_transport_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = client.request(method, url, **kwargs)
        except httpx.TransportError as exc:
            last_transport_error = exc
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
                continue
            break

        if response.status_code not in RETRYABLE_STATUS_CODES or attempt + 1 == attempts:
            return response

        retry_after = response.headers.get("Retry-After", "")
        delay = int(retry_after) if retry_after.isdigit() else 2**attempt
        time.sleep(min(max(delay, 1), 30))

    error_name = type(last_transport_error).__name__ if last_transport_error else "TransportError"
    raise ProviderResponseError(f"{provider_name} request failed ({error_name}).")


def response_json(response: httpx.Response, provider_name: str) -> Any:
    if not 200 <= response.status_code < 300:
        raise ProviderResponseError(
            f"{provider_name} request failed with HTTP {response.status_code}."
        )
    try:
        return response.json()
    except ValueError as exc:
        raise ProviderResponseError(f"{provider_name} returned invalid JSON.") from exc
