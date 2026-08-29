from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel, Topic


class Category(TimeStampedModel):
    name = models.CharField("名称", max_length=80, unique=True)
    slug = models.SlugField("标识", max_length=100, unique=True)
    description = models.CharField("描述", max_length=240, blank=True)
    sort_order = models.PositiveIntegerField("排序", default=0)

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name = "文章分类"
        verbose_name_plural = "文章分类"

    def __str__(self) -> str:
        return self.name


class ArticleQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Article.Status.PUBLISHED, published_at__lte=timezone.now())


class Article(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        PUBLISHED = "published", "已发布"
        ARCHIVED = "archived", "已归档"

    title = models.CharField("标题", max_length=200)
    slug = models.SlugField("标识", max_length=220, unique=True)
    summary = models.TextField("摘要")
    body_markdown = models.TextField("Markdown 正文")
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="articles", verbose_name="分类"
    )
    topics = models.ManyToManyField(Topic, blank=True, related_name="articles")
    status = models.CharField(
        "状态", max_length=16, choices=Status.choices, default=Status.DRAFT
    )
    published_at = models.DateTimeField("发布时间", blank=True, null=True)
    reading_minutes = models.PositiveSmallIntegerField("阅读分钟数", default=5)
    repository_url = models.URLField("相关代码", blank=True)
    is_featured = models.BooleanField("精选", default=False)
    is_demo = models.BooleanField("演示数据", default=False)
    seo_title = models.CharField("SEO 标题", max_length=200, blank=True)
    seo_description = models.CharField("SEO 描述", max_length=240, blank=True)

    objects = ArticleQuerySet.as_manager()

    class Meta:
        ordering = ("-published_at", "-created_at")
        indexes = [
            models.Index(fields=("status", "published_at")),
            models.Index(fields=("category", "status", "published_at")),
        ]
        verbose_name = "文章"
        verbose_name_plural = "文章"

    def __str__(self) -> str:
        return self.title
