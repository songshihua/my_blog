from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone

from apps.core.models import TimeStampedModel, Topic

from .storage import note_source_storage

MAX_CATEGORY_DEPTH = 8


def note_source_upload_to(instance: ArticleSourceFile, _filename: str) -> str:
    """Generate a server-owned path; the browser filename is never trusted."""

    now = timezone.now()
    extension = "md" if instance.source_format == "markdown" else instance.source_format
    return f"{now:%Y/%m}/{uuid.uuid4().hex}.{extension}"


class Category(TimeStampedModel):
    name = models.CharField("名称", max_length=80, unique=True)
    slug = models.SlugField("标识", max_length=100, unique=True)
    description = models.CharField("描述", max_length=240, blank=True)
    sort_order = models.PositiveIntegerField("排序", default=0)
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="children",
        verbose_name="上级分类",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("sort_order", "name")
        indexes = [models.Index(fields=("parent", "sort_order", "name"))]
        verbose_name = "文章分类"
        verbose_name_plural = "文章分类"

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        if self.pk and self.parent_id == self.pk:
            raise ValidationError({"parent": "分类不能将自己设为上级分类。"})

        seen = {self.pk} if self.pk else set()
        ancestor = self.parent
        depth = 1
        while ancestor is not None:
            if ancestor.pk in seen:
                raise ValidationError({"parent": "分类层级中存在循环关系。"})
            if depth >= MAX_CATEGORY_DEPTH:
                raise ValidationError({"parent": f"分类层级最多支持 {MAX_CATEGORY_DEPTH} 层。"})
            if ancestor.pk:
                seen.add(ancestor.pk)
            ancestor = ancestor.parent
            depth += 1

    def ancestors(self) -> list[Category]:
        result: list[Category] = []
        seen: set[int] = set()
        ancestor = self.parent
        while ancestor is not None and ancestor.pk not in seen:
            if ancestor.pk:
                seen.add(ancestor.pk)
            result.append(ancestor)
            ancestor = ancestor.parent
        result.reverse()
        return result


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
    status = models.CharField("状态", max_length=16, choices=Status.choices, default=Status.DRAFT)
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


class ArticleSourceFile(TimeStampedModel):
    class SourceFormat(models.TextChoices):
        MARKDOWN = "markdown", "Markdown"
        DOCX = "docx", "Word DOCX"
        PDF = "pdf", "PDF"

    article = models.OneToOneField(
        Article,
        on_delete=models.CASCADE,
        related_name="source_file",
        verbose_name="文章",
    )
    file = models.FileField(
        "原始文件",
        storage=note_source_storage,
        upload_to=note_source_upload_to,
        max_length=240,
    )
    original_filename = models.CharField("原文件名", max_length=240)
    source_format = models.CharField("文件格式", max_length=16, choices=SourceFormat.choices)
    content_type = models.CharField("内容类型", max_length=120)
    size_bytes = models.PositiveBigIntegerField("文件大小")
    sha256 = models.CharField("SHA-256", max_length=64, unique=True)
    outline = models.JSONField("文章目录", default=list, blank=True)
    extracted_at = models.DateTimeField("提取时间", default=timezone.now)

    class Meta:
        verbose_name = "笔记源文件"
        verbose_name_plural = "笔记源文件"

    def __str__(self) -> str:
        return self.original_filename


@receiver(post_delete, sender=ArticleSourceFile)
def delete_note_source_file(sender, instance: ArticleSourceFile, **_kwargs) -> None:
    """Remove private bytes only after the deleting transaction commits."""

    del sender
    storage = instance.file.storage
    name = instance.file.name
    if name:
        transaction.on_commit(lambda: storage.delete(name))
