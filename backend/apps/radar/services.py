"""Transactional synchronization from validated provider records into Django models."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from django.db import connection, transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.core.models import Topic
from apps.portfolio.models import Project

from .models import IngestionRun, RadarItem, RadarSource
from .providers import build_provider
from .providers.base import ExternalRecord, ProviderBatch, ProviderError, RemoteProvider, clean_text

SOURCE_DEFAULTS = {
    RadarSource.SourceType.GITHUB: (
        "GitHub 热门项目",
        "https://github.com/search?q=llm&type=repositories",
    ),
    RadarSource.SourceType.HUGGINGFACE: ("Hugging Face Hub", "https://huggingface.co/"),
    RadarSource.SourceType.DEEPSEEK: ("DeepSeek AI Search", "https://api.deepseek.com/"),
    RadarSource.SourceType.ARXIV: ("arXiv API", "https://arxiv.org/"),
    RadarSource.SourceType.OPENREVIEW: ("OpenReview", "https://openreview.net/"),
}

TOPIC_RULES = {
    "speculative-decoding": (
        "Speculative Decoding",
        ("speculative decoding", "speculative-decoding", "draft model"),
    ),
    "kv-cache": ("KV Cache", ("kv cache", "kv-cache", "paged attention", "pagedattention")),
    "llm-serving": (
        "LLM Serving",
        ("llm serving", "llm-serving", "vllm", "tgi", "inference server"),
    ),
    "continuous-batching": (
        "Continuous Batching",
        ("continuous batching", "continuous-batching", "dynamic batching"),
    ),
    "quantization": (
        "Quantization",
        ("quantization", "quantized", "gguf", "gptq", "awq", "int8", "int4"),
    ),
    "long-context": (
        "Long Context",
        ("long context", "long-context", "context window", "rope"),
    ),
}


@dataclass(frozen=True, slots=True)
class SyncOutcome:
    status: str
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    message: str = ""


@dataclass(frozen=True, slots=True)
class SourceSyncResult:
    source_type: str
    name: str
    outcome: SyncOutcome


class RadarSyncAlreadyRunning(RuntimeError):
    """Another process currently owns the cross-process ingestion lock."""


@contextmanager
def radar_sync_lock(name: str = "song_blog_ingest_sources") -> Iterator[None]:
    """Use a MySQL named lock so API and management jobs cannot overlap."""

    if connection.vendor != "mysql":
        # MySQL is used by every deployed environment; this branch keeps unit
        # tests and local tooling portable without pretending to be cross-process.
        yield
        return

    with connection.cursor() as cursor:
        cursor.execute("SELECT GET_LOCK(%s, 0)", [name])
        row = cursor.fetchone()
        acquired = bool(row and row[0] == 1)
    if not acquired:
        raise RadarSyncAlreadyRunning("Another radar synchronization is already running.")
    try:
        yield
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT RELEASE_LOCK(%s)", [name])


def synchronize_source_types(
    source_types: Iterable[str] | None,
    *,
    limit: int,
    dry_run: bool = False,
) -> list[SourceSyncResult]:
    """Synchronize explicit sources, or all enabled sources when omitted."""

    bounded_limit = max(1, min(limit, 100))
    if source_types is None:
        sources = list(RadarSource.objects.filter(is_enabled=True))
    else:
        sources = []
        for source_type in dict.fromkeys(source_types):
            defaults = SOURCE_DEFAULTS.get(source_type)
            if defaults is None:
                continue
            name, homepage = defaults
            source, created = RadarSource.objects.get_or_create(
                source_type=source_type,
                defaults={"name": name, "homepage_url": homepage},
            )
            if not created and (source.name != name or source.homepage_url != homepage):
                source.name = name
                source.homepage_url = homepage
                source.save(update_fields=("name", "homepage_url", "updated_at"))
            sources.append(source)

    if not sources:
        return []

    results: list[SourceSyncResult] = []
    with radar_sync_lock():
        synchronizer = SourceSynchronizer()
        for source in sources:
            outcome = synchronizer.sync(
                source,
                build_provider(source),
                limit=bounded_limit,
                dry_run=dry_run,
            )
            results.append(
                SourceSyncResult(
                    source_type=source.source_type,
                    name=source.name,
                    outcome=outcome,
                )
            )
    return results


class SourceSynchronizer:
    def sync(
        self,
        source: RadarSource,
        provider: RemoteProvider | None,
        *,
        limit: int,
        dry_run: bool,
    ) -> SyncOutcome:
        now = timezone.now()
        run = IngestionRun.objects.create(source=source, status=IngestionRun.Status.RUNNING)
        source.status = RadarSource.Status.RUNNING
        source.last_attempt_at = now
        source.save(update_fields=("status", "last_attempt_at", "updated_at"))

        configuration_error = (
            "Provider adapter is not implemented."
            if provider is None
            else provider.configuration_error()
        )
        if configuration_error:
            return self._finish_skipped(source, run, configuration_error)
        if dry_run:
            return self._finish_skipped(source, run, "Dry run completed; no network call was made.")

        try:
            batch = provider.fetch(limit)
            outcome = self._persist_batch(source, batch)
        except Exception as exc:
            return self._finish_failed(source, run, exc)

        finished_at = timezone.now()
        run.status = IngestionRun.Status.SUCCESS
        run.finished_at = finished_at
        run.inserted_count = outcome.inserted
        run.updated_count = outcome.updated
        run.skipped_count = outcome.skipped
        run.save(
            update_fields=(
                "status",
                "finished_at",
                "inserted_count",
                "updated_count",
                "skipped_count",
                "updated_at",
            )
        )
        source.status = RadarSource.Status.SUCCESS
        source.last_success_at = finished_at
        if not batch.not_modified:
            source.last_item_count = len(batch.records)
        source.last_error_summary = ""
        source.sync_state = batch.sync_state
        update_fields = [
            "status",
            "last_success_at",
            "last_error_summary",
            "sync_state",
            "updated_at",
        ]
        if not batch.not_modified:
            update_fields.append("last_item_count")
        source.save(update_fields=update_fields)
        return outcome

    def _persist_batch(self, source: RadarSource, batch: ProviderBatch) -> SyncOutcome:
        if batch.not_modified:
            return SyncOutcome(
                status=IngestionRun.Status.SUCCESS,
                skipped=1,
                message="Not modified.",
            )

        inserted = updated = skipped = 0
        with transaction.atomic():
            if (
                source.source_type == RadarSource.SourceType.GITHUB
                and batch.sync_state.get("mode") == "discovery"
                and source.sync_state.get("mode") != "discovery"
            ):
                # The former provider represented one user's repository list.
                # Hide those legacy radar rows when switching to public
                # discovery, while leaving personal portfolio projects intact.
                current_ids = [record.external_id for record in batch.records]
                RadarItem.objects.filter(source=source, is_demo=False).exclude(
                    external_id__in=current_ids
                ).update(is_visible=False)
            for record in batch.records:
                topics = self._topics_for_record(record)
                item, created, changed = self._upsert_radar_item(source, record, topics)
                if created:
                    inserted += 1
                elif changed:
                    updated += 1
                else:
                    skipped += 1
                if record.project is not None:
                    self._upsert_github_project(record, topics)
                # Keep the object reference alive until all many-to-many writes complete.
                _ = item
            if (
                source.source_type == RadarSource.SourceType.GITHUB
                and batch.sync_state.get("snapshot_complete") is True
            ):
                self._retire_missing_github_records(source, batch.records)
        return SyncOutcome(
            status=IngestionRun.Status.SUCCESS,
            inserted=inserted,
            updated=updated,
            skipped=skipped,
        )

    @staticmethod
    def _topics_for_record(record: ExternalRecord) -> list[Topic]:
        haystack = " ".join(
            [record.title, record.summary, *record.topics]
        ).casefold()
        matched: list[Topic] = []
        for slug, (name, keywords) in TOPIC_RULES.items():
            if any(keyword in haystack for keyword in keywords):
                topic, _ = Topic.objects.get_or_create(
                    slug=slug,
                    defaults={"name": name, "color": "#315CFF"},
                )
                matched.append(topic)
        return matched

    @staticmethod
    def _upsert_radar_item(
        source: RadarSource, record: ExternalRecord, topics: list[Topic]
    ) -> tuple[RadarItem, bool, bool]:
        defaults: dict[str, Any] = {
            "kind": record.kind,
            "title": record.title,
            "original_url": record.original_url,
            "summary": record.summary,
            "ai_summary": record.ai_summary,
            "authors": record.authors,
            "metadata": record.metadata,
            "published_at": record.published_at,
            "relevance_score": record.relevance_score,
            "is_demo": False,
        }
        item = RadarItem.objects.filter(source=source, external_id=record.external_id).first()
        if item is None:
            item = RadarItem.objects.create(
                source=source,
                external_id=record.external_id,
                is_visible=True,
                **defaults,
            )
            item.topics.set(topics)
            return item, True, True

        changed = any(getattr(item, field) != value for field, value in defaults.items())
        existing_topic_ids = set(item.topics.values_list("id", flat=True))
        topic_ids = {topic.id for topic in topics}
        changed = changed or existing_topic_ids != topic_ids
        if changed:
            for field, value in defaults.items():
                setattr(item, field, value)
            item.save()
            item.topics.set(topics)
        return item, False, changed

    @staticmethod
    def _retire_missing_github_records(
        source: RadarSource, records: list[ExternalRecord]
    ) -> None:
        """Conservatively hide records absent from a proven-complete snapshot."""

        external_ids = [record.external_id for record in records]
        RadarItem.objects.filter(source=source, is_demo=False).exclude(
            external_id__in=external_ids
        ).update(is_visible=False)
        Project.objects.filter(external_source=Project.ExternalSource.GITHUB).exclude(
            external_id__in=external_ids
        ).update(is_published=False, last_synced_at=timezone.now())

    @staticmethod
    def _upsert_github_project(record: ExternalRecord, topics: list[Topic]) -> Project:
        assert record.project is not None
        project = Project.objects.filter(
            external_source=Project.ExternalSource.GITHUB,
            external_id=record.external_id,
        ).first()
        synced_fields = {
            "title": record.project["title"],
            "subtitle": record.project["subtitle"],
            "summary": record.project["summary"],
            "repository_url": record.project["repository_url"],
            "demo_url": record.project["demo_url"],
            "started_at": record.project["started_at"],
            "source_metadata": record.project["source_metadata"],
            "last_synced_at": timezone.now(),
            "is_demo": False,
        }
        if project is None:
            base_slug = slugify(f"{record.project['title']}-{record.external_id}")
            candidate = (base_slug or f"github-project-{record.external_id}")[:180]
            suffix = 1
            while Project.objects.filter(slug=candidate).exists():
                suffix += 1
                candidate = f"{base_slug[:170]}-{suffix}"[:180]
            project = Project.objects.create(
                slug=candidate,
                category=SourceSynchronizer._infer_project_category(record),
                is_published=True,
                is_featured=False,
                sort_order=1000,
                external_source=Project.ExternalSource.GITHUB,
                external_id=record.external_id,
                **synced_fields,
            )
        else:
            for field, value in synced_fields.items():
                setattr(project, field, value)
            project.save()
        project.topics.set(topics)
        return project

    @staticmethod
    def _infer_project_category(record: ExternalRecord) -> str:
        text = " ".join([record.title, record.summary, *record.topics]).casefold()
        if any(keyword in text for keyword in ("inference", "serving", "vllm", "cache")):
            return Project.Category.SYSTEM
        if any(keyword in text for keyword in ("tutorial", "learning", "notes")):
            return Project.Category.LEARNING
        return Project.Category.TOOL

    @staticmethod
    def _finish_skipped(
        source: RadarSource, run: IngestionRun, message: str
    ) -> SyncOutcome:
        run.status = IngestionRun.Status.SKIPPED
        run.skipped_count = 1
        run.finished_at = timezone.now()
        run.error_summary = clean_text(message, 500)
        run.save(
            update_fields=(
                "status",
                "skipped_count",
                "finished_at",
                "error_summary",
                "updated_at",
            )
        )
        source.status = (
            RadarSource.Status.IDLE if source.is_enabled else RadarSource.Status.DISABLED
        )
        source.last_item_count = 0
        source.save(update_fields=("status", "last_item_count", "updated_at"))
        return SyncOutcome(status=run.status, skipped=1, message=message)

    @staticmethod
    def _finish_failed(
        source: RadarSource, run: IngestionRun, exception: Exception
    ) -> SyncOutcome:
        if isinstance(exception, ProviderError):
            message = clean_text(str(exception), 500)
        else:
            message = f"{type(exception).__name__}: synchronization failed."
        finished_at = timezone.now()
        run.status = IngestionRun.Status.FAILED
        run.error_count = 1
        run.finished_at = finished_at
        run.error_summary = message
        run.save(
            update_fields=(
                "status",
                "error_count",
                "finished_at",
                "error_summary",
                "updated_at",
            )
        )
        source.status = RadarSource.Status.ERROR
        source.last_error_at = finished_at
        source.last_error_summary = message
        source.last_item_count = 0
        source.save(
            update_fields=(
                "status",
                "last_error_at",
                "last_error_summary",
                "last_item_count",
                "updated_at",
            )
        )
        return SyncOutcome(status=run.status, message=message)
