from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.blog.models import Article
from apps.portfolio.models import Project
from apps.radar.models import IngestionRun, RadarItem, RadarSource
from apps.radar.services import RadarSyncAlreadyRunning, SourceSyncResult, SyncOutcome


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_health_endpoints(api_client):
    assert api_client.get(reverse("health-live")).status_code == 200
    assert api_client.get(reverse("health-ready")).status_code == 200


@pytest.mark.django_db
def test_home_is_public_and_aggregated(api_client, profile, project, published_article, radar_item):
    response = api_client.get(reverse("home"))
    assert response.status_code == 200
    assert response.data["profile"]["name"] == profile.name
    assert response.data["featured_projects"][0]["slug"] == project.slug
    assert response.data["recent_articles"][0]["slug"] == published_article.slug
    assert response.data["radar_items"][0]["id"] == radar_item.id


@pytest.mark.django_db
def test_draft_and_future_articles_are_not_public(api_client, category, published_article):
    Article.objects.create(
        title="草稿",
        slug="draft",
        summary="不能公开",
        body_markdown="draft",
        category=category,
        status=Article.Status.DRAFT,
    )
    Article.objects.create(
        title="未来文章",
        slug="future",
        summary="尚未到发布时间",
        body_markdown="future",
        category=category,
        status=Article.Status.PUBLISHED,
        published_at=timezone.now() + timedelta(days=1),
    )

    response = api_client.get(reverse("article-list"))
    assert response.status_code == 200
    slugs = {item["slug"] for item in response.data["results"]}
    assert slugs == {published_article.slug}


@pytest.mark.django_db
def test_article_search(api_client, published_article):
    response = api_client.get(reverse("article-list"), {"search": "公开"})
    assert response.status_code == 200
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_radar_api_exposes_source_status_and_ai_summary(api_client, radar_item):
    radar_item.ai_summary = {"核心内容": "经过验证的结构化摘要"}
    radar_item.save(update_fields=("ai_summary", "updated_at"))

    item_response = api_client.get(reverse("radar-item-list"))
    source_response = api_client.get(reverse("radar-source-list"))

    assert item_response.status_code == 200
    assert item_response.data["results"][0]["ai_summary"]["核心内容"]
    assert source_response.status_code == 200
    assert source_response.data[0]["source_type"] == "arxiv"
    assert source_response.data[0]["is_configured"] is True
    assert "token" not in str(source_response.data).lower()


@pytest.mark.django_db
def test_radar_public_endpoints_exclude_demo_items(api_client, radar_item, radar_source):
    RadarItem.objects.create(
        source=radar_source,
        external_id="sample-item",
        kind=RadarItem.Kind.MODEL,
        title="Sample model",
        original_url="https://example.com/sample",
        published_at=timezone.now(),
        is_demo=True,
    )

    item_response = api_client.get(reverse("radar-item-list"))
    stats_response = api_client.get(reverse("radar-stats"))

    assert item_response.status_code == 200
    assert [item["id"] for item in item_response.data["results"]] == [radar_item.id]
    assert stats_response.status_code == 200
    assert stats_response.data["total_count"] == 1
    assert stats_response.data["by_kind"] == {RadarItem.Kind.PAPER: 1}
    assert stats_response.data["contains_demo_data"] is False


@pytest.mark.django_db
def test_radar_api_exposes_only_safe_github_repository_metrics(api_client):
    source = RadarSource.objects.create(
        name="GitHub 热门项目",
        source_type=RadarSource.SourceType.GITHUB,
        homepage_url="https://github.com/search",
    )
    RadarItem.objects.create(
        source=source,
        external_id="42",
        kind=RadarItem.Kind.REPOSITORY,
        title="community-llm-tool",
        original_url="https://github.com/community/llm-tool",
        published_at=timezone.now(),
        metadata={
            "stars": 321,
            "forks": 45,
            "language": "Python",
            "internal_note": "must not be serialized in list responses",
        },
    )

    response = api_client.get(reverse("radar-item-list"))
    source_response = api_client.get(reverse("radar-source-list"))

    assert response.status_code == 200
    assert source_response.status_code == 200
    assert source_response.data[0]["is_configured"] is True
    item = response.data["results"][0]
    assert item["repository_metrics"] == {
        "stars": 321,
        "forks": 45,
        "language": "Python",
    }
    assert "metadata" not in item
    assert "internal_note" not in str(item)


@pytest.mark.django_db
def test_trusted_local_frontend_can_trigger_bounded_radar_sync(api_client, monkeypatch, settings):
    settings.DEBUG = True
    settings.RADAR_BROWSER_SYNC_ENABLED = True
    settings.RADAR_BROWSER_SYNC_COOLDOWN_SECONDS = 30
    settings.RADAR_SYNC_LIMIT = 100
    settings.CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]
    captured = {}

    def fake_sync(source_types, *, limit, dry_run=False):
        captured["source_types"] = tuple(source_types)
        captured["limit"] = limit
        captured["dry_run"] = dry_run
        return [
            SourceSyncResult(
                source_type="arxiv",
                name="arXiv API",
                outcome=SyncOutcome(
                    status=IngestionRun.Status.SUCCESS,
                    inserted=2,
                    skipped=1,
                ),
            )
        ]

    monkeypatch.setattr("apps.radar.views.synchronize_source_types", fake_sync)
    response = api_client.post(
        reverse("radar-sync"),
        HTTP_ORIGIN="http://localhost:3000",
        REMOTE_ADDR="127.0.0.1",
    )

    assert response.status_code == 200
    assert response.data["status"] == "success"
    assert response.data["inserted"] == 2
    assert captured == {
        "source_types": ("arxiv", "github", "huggingface"),
        "limit": 20,
        "dry_run": False,
    }


@pytest.mark.django_db
def test_radar_sync_rejects_untrusted_origin_before_network_call(api_client, monkeypatch, settings):
    settings.DEBUG = True
    settings.RADAR_BROWSER_SYNC_ENABLED = True
    settings.CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]

    def unexpected_sync(*_args, **_kwargs):
        raise AssertionError("untrusted requests must not reach providers")

    monkeypatch.setattr("apps.radar.views.synchronize_source_types", unexpected_sync)
    response = api_client.post(
        reverse("radar-sync"),
        HTTP_ORIGIN="https://malicious.example",
        REMOTE_ADDR="127.0.0.1",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_radar_sync_reports_existing_job(api_client, monkeypatch, settings):
    settings.DEBUG = True
    settings.RADAR_BROWSER_SYNC_ENABLED = True
    settings.RADAR_BROWSER_SYNC_COOLDOWN_SECONDS = 30
    settings.CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]

    def busy_sync(*_args, **_kwargs):
        raise RadarSyncAlreadyRunning

    monkeypatch.setattr("apps.radar.views.synchronize_source_types", busy_sync)
    response = api_client.post(
        reverse("radar-sync"),
        HTTP_ORIGIN="http://localhost:3000",
        REMOTE_ADDR="127.0.0.1",
    )

    assert response.status_code == 409
    assert "正在运行" in response.data["detail"]


@pytest.mark.django_db
def test_trusted_local_frontend_can_generate_radar_brief(
    api_client, monkeypatch, settings, radar_item
):
    settings.DEBUG = True
    settings.RADAR_BRIEF_GENERATION_ENABLED = True
    settings.CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]
    settings.LLM_API_KEY = "test-key"
    monkeypatch.setattr(
        "apps.radar.views.RadarBriefGenerator.generate",
        lambda _self: {
            "title": "今日简报",
            "overview": "一条真实研究更新。",
            "highlights": [
                {
                    "item_id": radar_item.id,
                    "title": radar_item.title,
                    "url": radar_item.original_url,
                    "insight": "值得关注。",
                }
            ],
            "trends": [],
            "watchlist": [],
            "source_count": 1,
            "period_start": radar_item.published_at.isoformat(),
            "period_end": radar_item.published_at.isoformat(),
            "generated_at": radar_item.published_at.isoformat(),
            "model": "deepseek-v4-pro",
            "cached": False,
        },
    )

    response = api_client.post(
        reverse("radar-brief"),
        HTTP_ORIGIN="http://localhost:3000",
        REMOTE_ADDR="127.0.0.1",
    )

    assert response.status_code == 200
    assert response.data["title"] == "今日简报"
    assert response.data["highlights"][0]["item_id"] == radar_item.id


@pytest.mark.django_db
def test_radar_brief_rejects_untrusted_origin(api_client, monkeypatch, settings):
    settings.DEBUG = True
    settings.RADAR_BRIEF_GENERATION_ENABLED = True
    settings.CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]

    def unexpected_generate(_self):
        raise AssertionError("untrusted requests must not invoke the LLM")

    monkeypatch.setattr(
        "apps.radar.views.RadarBriefGenerator.generate", unexpected_generate
    )
    response = api_client.post(
        reverse("radar-brief"),
        HTTP_ORIGIN="https://malicious.example",
        REMOTE_ADDR="127.0.0.1",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_project_api_exposes_safe_github_metadata(api_client, project):
    project.external_source = Project.ExternalSource.GITHUB
    project.external_id = "987654"
    project.source_metadata = {"stars": 12, "language": "Python"}
    project.last_synced_at = timezone.now()
    project.is_demo = False
    project.save()

    response = api_client.get(reverse("project-list"))

    assert response.status_code == 200
    payload = response.data["results"][0]
    assert payload["external_source"] == "github"
    assert payload["source_metadata"] == {"stars": 12, "language": "Python"}
    assert payload["last_synced_at"] is not None
