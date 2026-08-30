"""Discover recently active, popular public repositories via GitHub Search."""

from __future__ import annotations

from contextlib import nullcontext
from datetime import date, timedelta
from decimal import Decimal
from math import log10
from typing import Any

import httpx
from django.conf import settings
from django.utils import timezone

from apps.radar.models import RadarItem, RadarSource

from .base import (
    ExternalRecord,
    ProviderBatch,
    ProviderResponseError,
    canonical_http_url,
    clean_string_list,
    clean_text,
    parse_timestamp,
    request_with_retries,
    response_json,
)


class GitHubProvider:
    """Return a bounded discovery feed instead of one account's repositories."""

    source_type = RadarSource.SourceType.GITHUB

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        sync_state: dict[str, Any] | None = None,
        today: date | None = None,
    ) -> None:
        self.token = settings.GITHUB_TOKEN
        self.api_version = settings.GITHUB_API_VERSION
        self.discovery_query = settings.GITHUB_DISCOVERY_QUERY
        self.lookback_days = settings.GITHUB_DISCOVERY_LOOKBACK_DAYS
        self.minimum_stars = settings.GITHUB_DISCOVERY_MIN_STARS
        self.sort = settings.GITHUB_DISCOVERY_SORT
        self.timeout = settings.EXTERNAL_HTTP_TIMEOUT_SECONDS
        self.user_agent = settings.EXTERNAL_HTTP_USER_AGENT
        self.client = client
        self.sync_state = sync_state or {}
        self.today = today or timezone.localdate()

    def configuration_error(self) -> str | None:
        if not self.discovery_query:
            return "GITHUB_DISCOVERY_QUERY is not configured."
        if len(self.discovery_query) > 256:
            return "GITHUB_DISCOVERY_QUERY must not exceed 256 characters."
        if self.token and not self.token.isascii():
            return "GITHUB_TOKEN must contain only ASCII characters."
        if self.sort not in {"stars", "forks", "help-wanted-issues", "updated"}:
            return "GITHUB_DISCOVERY_SORT is invalid."
        return None

    def fetch(self, limit: int) -> ProviderBatch:
        error = self.configuration_error()
        if error:
            raise ProviderResponseError(error)

        bounded_limit = max(1, min(limit, 100))
        cutoff = self.today - timedelta(days=self.lookback_days)
        search_query = self._build_search_query(cutoff)
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": self.user_agent,
            "X-GitHub-Api-Version": self.api_version,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        state_matches = (
            self.sync_state.get("mode") == "discovery"
            and self.sync_state.get("query") == search_query
            and self.sync_state.get("limit") == bounded_limit
            and self.sync_state.get("sort") == self.sort
        )
        if state_matches and self.sync_state.get("etag"):
            headers["If-None-Match"] = str(self.sync_state["etag"])

        manager = (
            nullcontext(self.client)
            if self.client is not None
            else httpx.Client(base_url="https://api.github.com", timeout=self.timeout)
        )
        with manager as client:
            response = request_with_retries(
                client,
                "GET",
                "/search/repositories",
                provider_name="GitHub",
                attempts=1,
                headers=headers,
                params={
                    "q": search_query,
                    "sort": self.sort,
                    "order": "desc",
                    "per_page": bounded_limit,
                    "page": 1,
                },
            )

        etag = response.headers.get("ETag", "")
        rate_limit_remaining = response.headers.get("X-RateLimit-Remaining", "")
        if response.status_code == 304:
            return ProviderBatch(
                records=[],
                sync_state={
                    **self.sync_state,
                    "etag": etag or self.sync_state.get("etag", ""),
                    "rate_limit_remaining": rate_limit_remaining,
                },
                not_modified=True,
            )

        if response.status_code in {403, 429}:
            raise ProviderResponseError(
                "GitHub Search is rate limited; configure GITHUB_TOKEN or retry later."
            )

        payload = response_json(response, "GitHub")
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise ProviderResponseError("GitHub returned an unexpected response shape.")

        records: list[ExternalRecord] = []
        seen_ids: set[str] = set()
        for repository in payload["items"]:
            if not isinstance(repository, dict):
                continue
            record = self._map_repository(repository)
            if record is None or record.external_id in seen_ids:
                continue
            records.append(record)
            seen_ids.add(record.external_id)
            if len(records) >= bounded_limit:
                break
        next_state = {
            "mode": "discovery",
            "query": search_query,
            "limit": bounded_limit,
            "sort": self.sort,
            "etag": etag,
            "rate_limit_remaining": rate_limit_remaining,
            "rate_limit_reset": response.headers.get("X-RateLimit-Reset", ""),
            "rate_limit_resource": response.headers.get("X-RateLimit-Resource", ""),
            "total_count": self._non_negative_int(payload.get("total_count")),
            "incomplete_results": bool(payload.get("incomplete_results")),
            # A top-N result is not a complete repository inventory. Missing
            # results must therefore never be automatically unpublished.
            "snapshot_complete": False,
        }
        return ProviderBatch(records=records, sync_state=next_state)

    def _build_search_query(self, cutoff: date) -> str:
        return " ".join(
            (
                self.discovery_query,
                "in:name,description,topics",
                f"stars:>={self.minimum_stars}",
                f"pushed:>={cutoff.isoformat()}",
                "archived:false",
                "is:public",
            )
        )

    def _map_repository(self, repository: dict[str, Any]) -> ExternalRecord | None:
        # Search normally excludes private repositories and forks, but the
        # provider validates the response as an additional trust boundary.
        if repository.get("private") or repository.get("fork") or repository.get("archived"):
            return None

        repository_id = repository.get("id")
        title = clean_text(repository.get("name"), 160)
        original_url = canonical_http_url(repository.get("html_url"))
        if not repository_id or not title or not original_url:
            return None

        full_name = clean_text(repository.get("full_name"), 200)
        description = clean_text(repository.get("description"), 1000)
        owner = repository.get("owner") if isinstance(repository.get("owner"), dict) else {}
        owner_login = clean_text(owner.get("login"), 100)
        if not owner_login and "/" in full_name:
            owner_login = full_name.split("/", maxsplit=1)[0]
        owner_login = owner_login or "GitHub"

        topics = clean_string_list(repository.get("topics"), limit=20, item_length=80)
        language = clean_text(repository.get("language"), 80)
        homepage = canonical_http_url(repository.get("homepage"), require_https=False)
        created_at = parse_timestamp(repository.get("created_at"))
        published_at = parse_timestamp(
            repository.get("pushed_at") or repository.get("updated_at"),
            fallback=created_at,
        )
        stars = self._non_negative_int(repository.get("stargazers_count"))
        forks = self._non_negative_int(repository.get("forks_count"))
        license_data = repository.get("license")
        license_id = (
            clean_text(license_data.get("spdx_id"), 80)
            if isinstance(license_data, dict)
            else ""
        )
        metadata = {
            "full_name": full_name,
            "language": language,
            "topics": topics,
            "stars": stars,
            "forks": forks,
            "open_issues": self._non_negative_int(repository.get("open_issues_count")),
            "license": license_id,
            "default_branch": clean_text(repository.get("default_branch"), 100),
            "homepage": homepage,
            "archived": False,
            "fork": False,
            "discovery_mode": "public_search_v1",
        }
        relevance = Decimal(
            str(min(99.0, 60.0 + log10(stars + 1) * 9.0))
        ).quantize(Decimal("0.01"))
        return ExternalRecord(
            external_id=str(repository_id),
            kind=RadarItem.Kind.REPOSITORY,
            title=title,
            original_url=original_url,
            summary=description,
            authors=[owner_login],
            published_at=published_at,
            topics=topics,
            metadata=metadata,
            relevance_score=relevance,
            # Discovered third-party repositories belong in the research radar,
            # not in the author's personal portfolio.
            project=None,
        )

    @staticmethod
    def _non_negative_int(value: object) -> int:
        try:
            return max(int(value or 0), 0)
        except (TypeError, ValueError):
            return 0
