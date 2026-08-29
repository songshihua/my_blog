import pytest
from django.utils import timezone

from apps.blog.models import Article, Category
from apps.core.models import SiteProfile, Topic
from apps.portfolio.models import Project
from apps.radar.models import RadarItem, RadarSource


@pytest.fixture
def topic(db):
    return Topic.objects.create(name="Speculative Decoding", slug="speculative-decoding")


@pytest.fixture
def category(db):
    return Category.objects.create(name="学习笔记", slug="notes")


@pytest.fixture
def profile(db):
    return SiteProfile.objects.create(
        name="测试用户",
        headline="测试简介",
        affiliation="测试学校",
        research_focus="推理优化",
    )


@pytest.fixture
def published_article(category, topic):
    article = Article.objects.create(
        title="公开文章",
        slug="published-article",
        summary="公开摘要",
        body_markdown="# 公开",
        category=category,
        status=Article.Status.PUBLISHED,
        published_at=timezone.now(),
    )
    article.topics.add(topic)
    return article


@pytest.fixture
def project(db, topic):
    instance = Project.objects.create(
        title="公开项目",
        slug="public-project",
        summary="项目摘要",
        is_published=True,
        is_featured=True,
    )
    instance.topics.add(topic)
    return instance


@pytest.fixture
def radar_source(db):
    return RadarSource.objects.create(
        name="arXiv",
        source_type=RadarSource.SourceType.ARXIV,
        homepage_url="https://arxiv.org/",
    )


@pytest.fixture
def radar_item(radar_source, topic):
    item = RadarItem.objects.create(
        source=radar_source,
        external_id="1234.5678",
        kind=RadarItem.Kind.PAPER,
        title="公开论文",
        original_url="https://arxiv.org/abs/1234.5678",
        published_at=timezone.now(),
    )
    item.topics.add(topic)
    return item
