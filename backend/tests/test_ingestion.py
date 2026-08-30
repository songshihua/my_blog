from datetime import UTC, date, datetime

import pytest
from django.core.management import call_command

from apps.portfolio.models import Project
from apps.radar.models import IngestionRun, RadarItem, RadarSource
from apps.radar.providers.base import ExternalRecord, ProviderBatch
from apps.radar.services import SourceSynchronizer


@pytest.mark.django_db
def test_ingestion_with_no_enabled_sources_is_a_noop(capsys, radar_source):
    call_command("ingest_sources", "--dry-run")

    assert IngestionRun.objects.count() == 0
    assert "No enabled radar sources" in capsys.readouterr().out


@pytest.mark.django_db
def test_unconfigured_provider_is_recorded_as_skipped(radar_source):
    radar_source.is_enabled = True
    radar_source.status = RadarSource.Status.IDLE
    radar_source.save()

    call_command("ingest_sources", "--source", radar_source.source_type, "--dry-run")

    run = IngestionRun.objects.get(source=radar_source)
    assert run.status == IngestionRun.Status.SKIPPED
    assert run.skipped_count == 1
    radar_source.refresh_from_db()
    assert radar_source.status == RadarSource.Status.IDLE


class FakeGitHubProvider:
    source_type = RadarSource.SourceType.GITHUB
    published_at = datetime(2026, 8, 29, tzinfo=UTC)

    def configuration_error(self):
        return None

    def fetch(self, limit):
        assert limit == 10
        return ProviderBatch(
            records=[
                ExternalRecord(
                    external_id="987",
                    kind=RadarItem.Kind.REPOSITORY,
                    title="production-serving",
                    original_url="https://github.com/example/production-serving",
                    summary="vLLM serving and KV Cache tools",
                    authors=["example"],
                    published_at=self.published_at,
                    topics=["vllm", "kv-cache"],
                    metadata={"stars": 7, "forks": 1, "language": "Python"},
                    project={
                        "title": "production-serving",
                        "subtitle": "Python · ★ 7",
                        "summary": "vLLM serving and KV Cache tools",
                        "repository_url": "https://github.com/example/production-serving",
                        "demo_url": "",
                        "started_at": date(2026, 8, 1),
                        "source_metadata": {
                            "stars": 7,
                            "forks": 1,
                            "language": "Python",
                        },
                    },
                )
            ],
            sync_state={"etag": "test"},
        )


@pytest.mark.django_db
def test_synchronizer_upserts_github_radar_and_project():
    source = RadarSource.objects.create(
        name="GitHub Projects",
        source_type=RadarSource.SourceType.GITHUB,
        homepage_url="https://github.com/",
        is_enabled=True,
    )
    synchronizer = SourceSynchronizer()

    first = synchronizer.sync(
        source, FakeGitHubProvider(), limit=10, dry_run=False
    )
    second = synchronizer.sync(
        source, FakeGitHubProvider(), limit=10, dry_run=False
    )

    assert first.inserted == 1
    assert second.skipped == 1
    assert RadarItem.objects.filter(source=source, external_id="987").count() == 1
    project = Project.objects.get(
        external_source=Project.ExternalSource.GITHUB,
        external_id="987",
    )
    assert project.is_published is True
    assert project.is_demo is False
    assert project.source_metadata["stars"] == 7

    item = RadarItem.objects.get(source=source, external_id="987")
    item.is_visible = False
    item.save(update_fields=("is_visible", "updated_at"))
    third = synchronizer.sync(source, FakeGitHubProvider(), limit=10, dry_run=False)
    item.refresh_from_db()
    assert third.skipped == 1
    assert item.is_visible is False


class EmptyCompleteGitHubProvider:
    source_type = RadarSource.SourceType.GITHUB

    def configuration_error(self):
        return None

    def fetch(self, _limit):
        return ProviderBatch(records=[], sync_state={"snapshot_complete": True})


@pytest.mark.django_db
def test_complete_github_snapshot_retires_missing_records():
    source = RadarSource.objects.create(
        name="GitHub Projects",
        source_type=RadarSource.SourceType.GITHUB,
        homepage_url="https://github.com/",
        is_enabled=True,
    )
    synchronizer = SourceSynchronizer()
    synchronizer.sync(source, FakeGitHubProvider(), limit=10, dry_run=False)

    synchronizer.sync(source, EmptyCompleteGitHubProvider(), limit=10, dry_run=False)

    item = RadarItem.objects.get(source=source, external_id="987")
    project = Project.objects.get(
        external_source=Project.ExternalSource.GITHUB,
        external_id="987",
    )
    assert item.is_visible is False
    assert project.is_published is False


class DiscoveryGitHubProvider:
    source_type = RadarSource.SourceType.GITHUB

    def configuration_error(self):
        return None

    def fetch(self, limit):
        assert limit == 10
        return ProviderBatch(
            records=[
                ExternalRecord(
                    external_id="123",
                    kind=RadarItem.Kind.REPOSITORY,
                    title="community-llm-tool",
                    original_url="https://github.com/community/llm-tool",
                    summary="A recently active public LLM repository.",
                    authors=["community"],
                    published_at=datetime(2026, 8, 29, tzinfo=UTC),
                    metadata={
                        "stars": 120,
                        "forks": 20,
                        "language": "Python",
                        "discovery_mode": "public_search_v1",
                    },
                    project=None,
                )
            ],
            sync_state={"mode": "discovery", "snapshot_complete": False},
        )


@pytest.mark.django_db
def test_discovery_switch_hides_legacy_feed_but_preserves_personal_project():
    source = RadarSource.objects.create(
        name="GitHub Projects",
        source_type=RadarSource.SourceType.GITHUB,
        homepage_url="https://github.com/",
        is_enabled=True,
    )
    synchronizer = SourceSynchronizer()
    synchronizer.sync(source, FakeGitHubProvider(), limit=10, dry_run=False)

    synchronizer.sync(source, DiscoveryGitHubProvider(), limit=10, dry_run=False)

    legacy_item = RadarItem.objects.get(source=source, external_id="987")
    discovered_item = RadarItem.objects.get(source=source, external_id="123")
    personal_project = Project.objects.get(
        external_source=Project.ExternalSource.GITHUB,
        external_id="987",
    )
    assert legacy_item.is_visible is False
    assert discovered_item.is_visible is True
    assert personal_project.is_published is True
    assert not Project.objects.filter(external_id="123").exists()


class NotModifiedGitHubProvider:
    source_type = RadarSource.SourceType.GITHUB

    def configuration_error(self):
        return None

    def fetch(self, _limit):
        return ProviderBatch(
            records=[],
            sync_state={"mode": "discovery", "etag": '"same"'},
            not_modified=True,
        )


@pytest.mark.django_db
def test_not_modified_sync_preserves_last_item_count():
    source = RadarSource.objects.create(
        name="GitHub 热门项目",
        source_type=RadarSource.SourceType.GITHUB,
        homepage_url="https://github.com/search",
        is_enabled=True,
        last_item_count=8,
        sync_state={"mode": "discovery", "etag": '"same"'},
    )

    outcome = SourceSynchronizer().sync(
        source,
        NotModifiedGitHubProvider(),
        limit=10,
        dry_run=False,
    )

    source.refresh_from_db()
    assert outcome.status == IngestionRun.Status.SUCCESS
    assert outcome.message == "Not modified."
    assert source.last_item_count == 8
