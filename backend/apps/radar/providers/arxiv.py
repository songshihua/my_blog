"""Read recent papers from arXiv's official Atom API."""

from __future__ import annotations

import re
from contextlib import nullcontext
from typing import Any
from urllib.parse import urlsplit

import feedparser
import httpx
from django.conf import settings

from apps.radar.models import RadarItem, RadarSource

from .base import (
    ExternalRecord,
    ProviderBatch,
    ProviderResponseError,
    clean_text,
    parse_timestamp,
    request_with_retries,
)

ARXIV_VERSION_SUFFIX = re.compile(r"v\d+$", re.IGNORECASE)


def _compact_text(value: object, max_length: int) -> str:
    """Collapse provider whitespace before applying database field bounds."""

    return clean_text(re.sub(r"\s+", " ", str(value or "")), max_length)


class ArxivProvider:
    """Fetch a bounded, newest-first paper feed without requiring credentials."""

    source_type = RadarSource.SourceType.ARXIV

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self.keywords = settings.AI_RADAR_KEYWORDS
        self.explicit_query = settings.ARXIV_SEARCH_QUERY
        self.timeout = settings.EXTERNAL_HTTP_TIMEOUT_SECONDS
        self.user_agent = settings.EXTERNAL_HTTP_USER_AGENT
        self.client = client

    def configuration_error(self) -> str | None:
        if not self.explicit_query and not self.keywords:
            return "Set ARXIV_SEARCH_QUERY or AI_RADAR_KEYWORDS."
        return None

    def fetch(self, limit: int) -> ProviderBatch:
        error = self.configuration_error()
        if error:
            raise ProviderResponseError(error)

        bounded_limit = max(1, min(limit, 20))
        query = self.explicit_query or self._query_from_keywords(self.keywords)
        manager = (
            nullcontext(self.client)
            if self.client is not None
            else httpx.Client(base_url="https://export.arxiv.org", timeout=self.timeout)
        )
        with manager as client:
            response = request_with_retries(
                client,
                "GET",
                "/api/query",
                provider_name="arXiv",
                params={
                    "search_query": query,
                    "start": 0,
                    "max_results": bounded_limit,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                },
                headers={
                    "Accept": "application/atom+xml",
                    "User-Agent": self.user_agent,
                },
            )

        if not 200 <= response.status_code < 300:
            raise ProviderResponseError(
                f"arXiv request failed with HTTP {response.status_code}."
            )

        feed = feedparser.parse(response.content)
        entries = list(feed.get("entries", []))
        if feed.get("bozo") and not entries:
            raise ProviderResponseError("arXiv returned an invalid Atom feed.")

        records: list[ExternalRecord] = []
        for entry in entries[:bounded_limit]:
            record = self._map_entry(entry)
            if record is not None:
                records.append(record)

        feed_metadata = feed.get("feed", {})
        return ProviderBatch(
            records=records,
            sync_state={
                "query": query,
                "limit": bounded_limit,
                "feed_updated": clean_text(feed_metadata.get("updated", ""), 80),
            },
        )

    @staticmethod
    def _query_from_keywords(keywords: list[str]) -> str:
        terms: list[str] = []
        for keyword in keywords[:10]:
            normalized = _compact_text(keyword, 100).replace('"', "").replace("\\", "")
            if not normalized:
                continue
            value = f'"{normalized}"' if " " in normalized else normalized
            terms.append(f"all:{value}")
        if not terms:
            raise ProviderResponseError("No valid arXiv search keywords are configured.")
        return f"({' OR '.join(terms)})"

    @staticmethod
    def _map_entry(entry: Any) -> ExternalRecord | None:
        raw_identifier = clean_text(entry.get("id", ""), 500)
        path = urlsplit(raw_identifier).path
        marker = "/abs/"
        if marker not in path:
            return None
        external_id = ARXIV_VERSION_SUFFIX.sub("", path.split(marker, 1)[1].strip("/"))
        title = _compact_text(entry.get("title", ""), 300)
        if not external_id or not title:
            return None

        authors = [
            _compact_text(author.get("name", ""), 100)
            for author in entry.get("authors", [])
            if _compact_text(author.get("name", ""), 100)
        ][:30]
        categories = [
            _compact_text(tag.get("term", ""), 100)
            for tag in entry.get("tags", [])
            if _compact_text(tag.get("term", ""), 100)
        ][:30]
        primary_category = clean_text(
            entry.get("arxiv_primary_category", {}).get("term", ""), 100
        )
        published_at = parse_timestamp(entry.get("published"))
        updated_at = parse_timestamp(entry.get("updated"), fallback=published_at)

        return ExternalRecord(
            external_id=external_id,
            kind=RadarItem.Kind.PAPER,
            title=title,
            original_url=f"https://arxiv.org/abs/{external_id}",
            summary=_compact_text(entry.get("summary", ""), 4000),
            authors=authors,
            published_at=published_at,
            topics=categories,
            metadata={
                "primary_category": primary_category,
                "categories": categories,
                "updated_at": updated_at.isoformat(),
                "pdf_url": f"https://arxiv.org/pdf/{external_id}",
                "comment": _compact_text(entry.get("arxiv_comment", ""), 500),
                "journal_reference": _compact_text(
                    entry.get("arxiv_journal_ref", ""), 500
                ),
                "doi": _compact_text(entry.get("arxiv_doi", ""), 200),
            },
        )
