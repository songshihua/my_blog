from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.blog.models import Article


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_health_endpoints(api_client):
    assert api_client.get(reverse("health-live")).status_code == 200
    assert api_client.get(reverse("health-ready")).status_code == 200


@pytest.mark.django_db
def test_home_is_public_and_aggregated(
    api_client, profile, project, published_article, radar_item
):
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
