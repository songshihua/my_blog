"""Read model and dataset metadata with the official Hugging Face Hub SDK."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from itertools import islice
from typing import Any

from django.conf import settings
from huggingface_hub import HfApi

from apps.radar.models import RadarItem, RadarSource

from .base import (
    ExternalRecord,
    ProviderBatch,
    ProviderResponseError,
    clean_string_list,
    clean_text,
    parse_timestamp,
)


class HuggingFaceProvider:
    source_type = RadarSource.SourceType.HUGGINGFACE

    def __init__(self, *, api: HfApi | Any | None = None) -> None:
        self.author = settings.HUGGINGFACE_AUTHOR
        self.search = settings.HUGGINGFACE_SEARCH
        self.token = settings.HUGGINGFACE_TOKEN
        self.include_datasets = settings.HUGGINGFACE_INCLUDE_DATASETS
        self.api = api

    def configuration_error(self) -> str | None:
        if not self.author and not self.search:
            return "Set HUGGINGFACE_AUTHOR or HUGGINGFACE_SEARCH."
        if self.token and not self.token.isascii():
            return "HUGGINGFACE_TOKEN must contain only ASCII characters."
        return None

    def fetch(self, limit: int) -> ProviderBatch:
        error = self.configuration_error()
        if error:
            raise ProviderResponseError(error)

        api = self.api or HfApi(
            endpoint="https://huggingface.co",
            token=self.token if self.token else False,
        )
        model_limit = limit if not self.include_datasets else max(1, (limit + 1) // 2)
        dataset_limit = max(limit - model_limit, 0)
        records: list[ExternalRecord] = []
        try:
            models = api.list_models(
                author=self.author or None,
                search=self.search or None,
                sort="last_modified",
                limit=model_limit,
                token=self.token if self.token else False,
            )
            for info in islice(models, model_limit):
                record = self._map_info(info, is_dataset=False)
                if record is not None:
                    records.append(record)

            if dataset_limit:
                datasets = api.list_datasets(
                    author=self.author or None,
                    search=self.search or None,
                    sort="last_modified",
                    limit=dataset_limit,
                    token=self.token if self.token else False,
                )
                for info in islice(datasets, dataset_limit):
                    record = self._map_info(info, is_dataset=True)
                    if record is not None:
                        records.append(record)
        except Exception as exc:
            raise ProviderResponseError(
                f"Hugging Face request failed ({type(exc).__name__})."
            ) from exc

        return ProviderBatch(
            records=records[:limit],
            sync_state={"author": self.author, "search": self.search, "limit": limit},
        )

    def _map_info(self, info: Any, *, is_dataset: bool) -> ExternalRecord | None:
        if bool(getattr(info, "private", False)):
            return None
        repository_id = clean_text(getattr(info, "id", ""), 200)
        if not repository_id:
            return None

        author = clean_text(getattr(info, "author", ""), 100)
        if not author and "/" in repository_id:
            author = repository_id.split("/", maxsplit=1)[0]
        created_at = getattr(info, "created_at", None) or getattr(info, "createdAt", None)
        last_modified = getattr(info, "last_modified", None) or getattr(
            info, "lastModified", None
        )
        fallback_time = created_at if isinstance(created_at, datetime) else None
        published_at = parse_timestamp(last_modified or created_at, fallback=fallback_time)
        tags = clean_string_list(getattr(info, "tags", []), limit=30, item_length=100)
        downloads = max(int(getattr(info, "downloads", 0) or 0), 0)
        likes = max(int(getattr(info, "likes", 0) or 0), 0)
        gated = getattr(info, "gated", False)
        sha = clean_text(getattr(info, "sha", ""), 80)

        if is_dataset:
            kind = RadarItem.Kind.DATASET
            original_url = f"https://huggingface.co/datasets/{repository_id}"
            description = clean_text(getattr(info, "description", ""), 1000)
            summary = description or (
                f"Hugging Face 数据集；下载量 {downloads}，点赞 {likes}。"
            )
            external_id = f"dataset:{repository_id}"
            metadata = {
                "repo_type": "dataset",
                "sha": sha,
                "tags": tags,
                "downloads": downloads,
                "likes": likes,
                "gated": gated,
            }
        else:
            kind = RadarItem.Kind.MODEL
            original_url = f"https://huggingface.co/{repository_id}"
            pipeline_tag = clean_text(getattr(info, "pipeline_tag", ""), 100)
            library_name = clean_text(getattr(info, "library_name", ""), 100)
            facts = [part for part in (pipeline_tag, library_name) if part]
            summary = "Hugging Face 模型"
            if facts:
                summary += f"；{', '.join(facts)}"
            summary += f"；下载量 {downloads}，点赞 {likes}。"
            external_id = f"model:{repository_id}"
            metadata = {
                "repo_type": "model",
                "sha": sha,
                "tags": tags,
                "downloads": downloads,
                "likes": likes,
                "gated": gated,
                "pipeline_tag": pipeline_tag,
                "library_name": library_name,
            }

        relevance = min(Decimal("99"), Decimal("55") + Decimal(min(likes, 44)))
        return ExternalRecord(
            external_id=external_id,
            kind=kind,
            title=repository_id,
            original_url=original_url,
            summary=summary[:1000],
            authors=[author] if author else [],
            published_at=published_at,
            topics=tags,
            metadata=metadata,
            relevance_score=relevance,
        )
