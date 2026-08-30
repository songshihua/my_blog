"""Use DeepSeek Responses API web search to discover recent AI knowledge."""

from __future__ import annotations

import hashlib
import json
from contextlib import nullcontext
from datetime import timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import urljoin

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
    host_is_allowed,
    parse_timestamp,
    request_with_retries,
    response_json,
)

KIND_MAP = {
    "paper": RadarItem.Kind.PAPER,
    "repository": RadarItem.Kind.REPOSITORY,
    "model": RadarItem.Kind.MODEL,
    "dataset": RadarItem.Kind.DATASET,
    "article": RadarItem.Kind.ARTICLE,
}
CONFIDENCE_SCORE = {
    "high": Decimal("92"),
    "medium": Decimal("76"),
    "low": Decimal("60"),
}


class DeepSeekProvider:
    source_type = RadarSource.SourceType.DEEPSEEK

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_BASE_URL
        self.model = settings.LLM_MODEL
        self.fallback_model = settings.LLM_FALLBACK_MODEL
        self.lookback_days = settings.LLM_LOOKBACK_DAYS
        self.reasoning_effort = settings.LLM_REASONING_EFFORT
        self.verify_source_urls = settings.LLM_VERIFY_SOURCE_URLS
        self.keywords = settings.AI_RADAR_KEYWORDS
        self.allowed_domains = settings.AI_RADAR_ALLOWED_DOMAINS
        self.timeout = settings.EXTERNAL_HTTP_TIMEOUT_SECONDS
        self.client = client

    def configuration_error(self) -> str | None:
        if not self.api_key:
            return "LLM_API_KEY is not configured."
        if not self.api_key.isascii():
            return "LLM_API_KEY must contain only ASCII characters."
        if not self.base_url or not self.model:
            return "LLM_BASE_URL and LLM_MODEL must be configured."
        if not self.keywords or not self.allowed_domains:
            return "AI radar keywords and allowed domains must be configured."
        return None

    def fetch(self, limit: int) -> ProviderBatch:
        error = self.configuration_error()
        if error:
            raise ProviderResponseError(error)

        manager = (
            nullcontext(self.client)
            if self.client is not None
            else httpx.Client(base_url=self.base_url, timeout=max(self.timeout, 90))
        )
        with manager as client:
            response, used_model = self._request(client, self.model, limit)
            payload = response_json(response, "DeepSeek")
            if payload.get("status") not in {None, "completed"}:
                raise ProviderResponseError("DeepSeek returned an incomplete response.")
            if not self._has_completed_web_search(payload):
                raise ProviderResponseError("DeepSeek did not complete the required web search.")
            output_text = self._extract_output_text(payload)
            try:
                structured = json.loads(output_text)
            except (TypeError, ValueError) as exc:
                raise ProviderResponseError("DeepSeek returned invalid structured JSON.") from exc
            records = self._map_items(structured.get("items"), used_model, limit, client)
        if not records:
            raise ProviderResponseError("DeepSeek returned no verifiable AI knowledge items.")
        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        safe_usage = {
            key: int(value)
            for key, value in usage.items()
            if key in {"input_tokens", "output_tokens", "total_tokens"}
            and isinstance(value, int)
        }
        return ProviderBatch(
            records=records,
            sync_state={"model": used_model, "usage": safe_usage, "limit": limit},
        )

    def _request(
        self, client: httpx.Client, model: str, limit: int
    ) -> tuple[httpx.Response, str]:
        response = request_with_retries(
            client,
            "POST",
            "/responses",
            provider_name="DeepSeek",
            # A timed-out or lost response may still have been billed upstream.
            # Never retry a metered generation request without an idempotency key.
            attempts=1,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=self._payload(model, limit),
        )
        if response.status_code == 400 and self.fallback_model and model != self.fallback_model:
            response = request_with_retries(
                client,
                "POST",
                "/responses",
                provider_name="DeepSeek",
                attempts=1,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=self._payload(self.fallback_model, limit),
            )
            return response, self.fallback_model
        return response, model

    def _payload(self, model: str, limit: int) -> dict[str, Any]:
        now = timezone.now()
        earliest = (now - timedelta(days=self.lookback_days)).date().isoformat()
        domains = ", ".join(self.allowed_domains)
        keywords = ", ".join(self.keywords)
        prompt = (
            f"当前日期是 {now.date().isoformat()}。联网检索 {earliest} 之后发布或更新的 AI "
            f"研究与工程进展，重点关注：{keywords}。只采用这些域名的原始来源：{domains}。"
            "不要把搜索摘要页、无法确认日期的内容或推测性 URL 纳入结果。"
            f"最多返回 {limit} 条，按研究相关性和新鲜度排序。"
        )
        item_schema = {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "title",
                "source_url",
                "kind",
                "published_at",
                "summary",
                "authors",
                "topics",
                "why_it_matters",
                "evidence",
                "confidence",
            ],
            "properties": {
                "title": {"type": "string", "maxLength": 300},
                "source_url": {"type": "string", "format": "uri"},
                "kind": {"type": "string", "enum": list(KIND_MAP)},
                "published_at": {"type": "string", "format": "date-time"},
                "summary": {"type": "string", "maxLength": 1200},
                "authors": {
                    "type": "array",
                    "maxItems": 20,
                    "items": {"type": "string", "maxLength": 100},
                },
                "topics": {
                    "type": "array",
                    "maxItems": 12,
                    "items": {"type": "string", "maxLength": 80},
                },
                "why_it_matters": {"type": "string", "maxLength": 600},
                "evidence": {"type": "string", "maxLength": 600},
                "confidence": {"type": "string", "enum": list(CONFIDENCE_SCORE)},
            },
        }
        return {
            "model": model,
            "instructions": (
                "你是研究情报编辑。必须使用 web_search，输出可追溯的最新 AI 知识 JSON；"
                "不得编造标题、发布日期、作者或来源 URL。"
            ),
            "input": prompt,
            "tools": [{"type": "web_search"}],
            "tool_choice": {"type": "web_search"},
            "reasoning": {"effort": self.reasoning_effort},
            "max_output_tokens": 5000,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "ai_radar_items",
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["items"],
                        "properties": {
                            "items": {
                                "type": "array",
                                "maxItems": limit,
                                "items": item_schema,
                            }
                        },
                    },
                }
            },
            "user": "ss-lab-radar",
        }

    @staticmethod
    def _extract_output_text(payload: dict[str, Any]) -> str:
        for output in payload.get("output", []):
            if not isinstance(output, dict) or output.get("type") != "message":
                continue
            for content in output.get("content", []):
                if isinstance(content, dict) and content.get("type") == "output_text":
                    text = content.get("text")
                    if isinstance(text, str) and text.strip():
                        return text
        raise ProviderResponseError("DeepSeek response did not contain output text.")

    @staticmethod
    def _has_completed_web_search(payload: dict[str, Any]) -> bool:
        return any(
            isinstance(output, dict)
            and output.get("type") == "web_search_call"
            and output.get("status") in {None, "completed"}
            for output in payload.get("output", [])
        )

    def _map_items(
        self, items: object, model: str, limit: int, client: httpx.Client
    ) -> list[ExternalRecord]:
        if not isinstance(items, list):
            return []
        now = timezone.now()
        earliest = now - timedelta(days=self.lookback_days + 2)
        latest = now + timedelta(days=1)
        records: list[ExternalRecord] = []
        seen_urls: set[str] = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            title = clean_text(item.get("title"), 300)
            url = canonical_http_url(item.get("source_url"))
            kind = KIND_MAP.get(str(item.get("kind", "")).lower())
            if not title or not url or not kind or not host_is_allowed(url, self.allowed_domains):
                continue
            if self.verify_source_urls and not self._verify_source_url(client, url):
                continue
            if url in seen_urls:
                continue
            try:
                published_at = parse_timestamp(item.get("published_at"))
            except ProviderResponseError:
                continue
            if not earliest <= published_at <= latest:
                continue

            confidence = str(item.get("confidence", "low")).lower()
            if confidence not in CONFIDENCE_SCORE:
                confidence = "low"
            summary = clean_text(item.get("summary"), 1200)
            why_it_matters = clean_text(item.get("why_it_matters"), 600)
            evidence = clean_text(item.get("evidence"), 600)
            external_id = hashlib.sha256(url.encode("utf-8")).hexdigest()
            records.append(
                ExternalRecord(
                    external_id=external_id,
                    kind=kind,
                    title=title,
                    original_url=url,
                    summary=summary,
                    authors=clean_string_list(item.get("authors")),
                    published_at=published_at,
                    topics=clean_string_list(item.get("topics"), limit=12, item_length=80),
                    metadata={
                        "retrieved_by": "deepseek_web_search",
                        "model": model,
                        "confidence": confidence,
                        "source_domain_validated": True,
                    },
                    ai_summary={
                        "核心内容": summary,
                        "研究价值": why_it_matters,
                        "可信度说明": f"{confidence.upper()} · {evidence}",
                    },
                    relevance_score=CONFIDENCE_SCORE[confidence],
                )
            )
            seen_urls.add(url)
            if len(records) >= limit:
                break
        return records

    def _verify_source_url(self, client: httpx.Client, url: str) -> bool:
        """Confirm an allow-listed public URL exists without downloading its body."""

        current_url = url
        for _redirect in range(4):
            try:
                response = request_with_retries(
                    client,
                    "HEAD",
                    current_url,
                    provider_name="Source verification",
                    attempts=2,
                    headers={"User-Agent": settings.EXTERNAL_HTTP_USER_AGENT},
                )
            except ProviderResponseError:
                return False
            if 200 <= response.status_code < 300:
                return True
            if response.status_code not in {301, 302, 303, 307, 308}:
                return False
            location = response.headers.get("Location")
            if not location:
                return False
            candidate = canonical_http_url(urljoin(current_url, location))
            if not candidate or not host_is_allowed(candidate, self.allowed_domains):
                return False
            current_url = candidate
        return False
