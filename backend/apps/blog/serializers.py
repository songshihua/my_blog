from __future__ import annotations

import re
import uuid

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.db.models import Max
from django.utils import timezone
from django.utils.text import slugify
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.reverse import reverse

from apps.core.serializers import TopicSerializer

from .importers import (
    MAX_EXTRACTED_CHARACTERS,
    _build_slug,
    _derive_summary,
    _reading_minutes,
    extract_outline,
)
from .models import (
    MAX_CATEGORY_DEPTH,
    Article,
    ArticleImage,
    ArticleSourceFile,
    Category,
)

NOTE_IMAGE_ID_PATTERN = re.compile(r"\b[0-9a-f]{32}\b", re.IGNORECASE)


class CategoryAncestorSerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.SlugField()


class CategorySerializer(serializers.ModelSerializer):
    parent_slug = serializers.SlugField(source="parent.slug", read_only=True, allow_null=True)
    ancestors = serializers.SerializerMethodField()

    @extend_schema_field(CategoryAncestorSerializer(many=True))
    def get_ancestors(self, obj: Category) -> list[dict[str, str]]:
        return [{"name": ancestor.name, "slug": ancestor.slug} for ancestor in obj.ancestors()]

    class Meta:
        model = Category
        fields = (
            "name",
            "slug",
            "description",
            "sort_order",
            "parent_slug",
            "ancestors",
        )


class CategoryCreateRequestSerializer(serializers.ModelSerializer):
    """Validate a browser-created logical directory and own its URL-safe slug."""

    parent_slug = serializers.SlugRelatedField(
        source="parent",
        slug_field="slug",
        queryset=Category.objects.all(),
        required=False,
        allow_null=True,
        error_messages={
            "does_not_exist": "所选上级目录不存在。",
            "invalid": "上级目录标识无效。",
        },
    )

    class Meta:
        model = Category
        fields = ("name", "parent_slug", "description")
        extra_kwargs = {
            "name": {
                "error_messages": {
                    "blank": "请输入目录名称。",
                    "unique": "已存在同名目录，请换一个名称。",
                }
            },
            "description": {"required": False, "allow_blank": True},
        }

    def validate_name(self, value: str) -> str:
        name = value.strip()
        if name in {".", ".."} or any(character in name for character in ("/", "\\")):
            raise serializers.ValidationError("目录名称不能是路径片段或包含斜杠。")
        if any(ord(character) < 32 for character in name):
            raise serializers.ValidationError("目录名称不能包含控制字符。")
        return name

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        attrs = super().validate(attrs)
        parent = attrs.get("parent")
        if isinstance(parent, Category) and len(parent.ancestors()) + 1 >= MAX_CATEGORY_DEPTH:
            raise serializers.ValidationError(
                {"parent_slug": f"目录层级最多支持 {MAX_CATEGORY_DEPTH} 层。"}
            )
        return attrs

    @staticmethod
    def _available_slug(name: str) -> str:
        base = slugify(name).replace("_", "-").strip("-")[:100] or "folder"
        if not Category.objects.filter(slug=base).exists():
            return base

        # Keep a readable prefix while making collisions between different names
        # overwhelmingly unlikely. The database unique constraint remains the guard.
        while True:
            candidate = f"{base[:91].rstrip('-')}-{uuid.uuid4().hex[:8]}"
            if not Category.objects.filter(slug=candidate).exists():
                return candidate

    def create(self, validated_data: dict[str, object]) -> Category:
        parent = validated_data.get("parent")
        sibling_max = Category.objects.filter(parent=parent).aggregate(
            maximum=Max("sort_order")
        )["maximum"]
        category = Category(
            **validated_data,
            slug=self._available_slug(str(validated_data["name"])),
            sort_order=(sibling_max or 0) + 10,
        )
        try:
            category.full_clean()
            category.save()
        except DjangoValidationError as exc:
            detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            raise serializers.ValidationError(detail) from exc
        except IntegrityError as exc:
            # A concurrent request can still win after serializer uniqueness checks.
            raise serializers.ValidationError(
                {"name": "目录名称或标识已存在，请换一个名称后重试。"}
            ) from exc
        return category


class ArticleSourceFileSerializer(serializers.ModelSerializer):
    source_format_label = serializers.CharField(source="get_source_format_display", read_only=True)
    download_url = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()

    @extend_schema_field(serializers.CharField())
    def get_download_url(self, obj: ArticleSourceFile) -> str:
        return reverse(
            "article-source-file",
            kwargs={"slug": obj.article.slug},
        )

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_preview_url(self, obj: ArticleSourceFile) -> str | None:
        if obj.source_format != ArticleSourceFile.SourceFormat.PDF:
            return None
        return reverse(
            "article-preview-file",
            kwargs={"slug": obj.article.slug},
        )

    class Meta:
        model = ArticleSourceFile
        fields = (
            "original_filename",
            "source_format",
            "source_format_label",
            "size_bytes",
            "download_url",
            "preview_url",
        )


class ArticleListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    topics = TopicSerializer(many=True, read_only=True)
    source_file = ArticleSourceFileSerializer(read_only=True, allow_null=True)

    class Meta:
        model = Article
        fields = (
            "title",
            "slug",
            "summary",
            "category",
            "topics",
            "published_at",
            "updated_at",
            "reading_minutes",
            "is_featured",
            "is_demo",
            "source_file",
        )


class ArticleDetailSerializer(ArticleListSerializer):
    outline = serializers.SerializerMethodField()

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_outline(self, obj: Article) -> list[dict[str, object]]:
        return extract_outline(obj.body_markdown)

    class Meta(ArticleListSerializer.Meta):
        fields = ArticleListSerializer.Meta.fields + (
            "body_markdown",
            "outline",
            "repository_url",
            "seo_title",
            "seo_description",
        )


class NoteTreeResponseSerializer(serializers.Serializer):
    categories = CategorySerializer(many=True)
    articles = ArticleListSerializer(many=True)
    import_enabled = serializers.BooleanField()
    authoring_enabled = serializers.BooleanField()
    max_category_depth = serializers.IntegerField()


class NoteWriteRequestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, trim_whitespace=True)
    summary = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )
    category_slug = serializers.SlugRelatedField(
        source="category",
        slug_field="slug",
        queryset=Category.objects.all(),
        error_messages={
            "does_not_exist": "所选笔记分类不存在。",
            "invalid": "笔记分类标识无效。",
        },
    )
    body_markdown = serializers.CharField(
        max_length=MAX_EXTRACTED_CHARACTERS,
        trim_whitespace=False,
    )

    def validate_title(self, value: str) -> str:
        title = " ".join(value.split())
        if not title:
            raise serializers.ValidationError("请输入笔记标题。")
        return title

    def validate_body_markdown(self, value: str) -> str:
        body = value.strip()
        if not body:
            raise serializers.ValidationError("请先写一些笔记内容。")
        return body

    def create(self, validated_data: dict[str, object]) -> Article:
        body = str(validated_data["body_markdown"])
        title = str(validated_data["title"])
        summary = str(validated_data.get("summary", "") or "").strip()
        article = Article.objects.create(
            title=title,
            slug=_build_slug(title, uuid.uuid4().hex),
            summary=summary or _derive_summary(body),
            body_markdown=body,
            category=validated_data["category"],
            status=Article.Status.PUBLISHED,
            published_at=timezone.now(),
            reading_minutes=_reading_minutes(body),
            is_demo=False,
            seo_title=title,
            seo_description=(summary or _derive_summary(body))[:240],
        )
        self._attach_images(article, body)
        return article

    def update(self, instance: Article, validated_data: dict[str, object]) -> Article:
        body = str(validated_data.get("body_markdown", instance.body_markdown))
        title = str(validated_data.get("title", instance.title))
        summary_value = validated_data.get("summary", instance.summary)
        summary = str(summary_value or "").strip() or _derive_summary(body)
        instance.title = title
        instance.summary = summary
        instance.body_markdown = body
        instance.category = validated_data.get("category", instance.category)
        instance.reading_minutes = _reading_minutes(body)
        instance.seo_title = title
        instance.seo_description = summary[:240]
        instance.is_demo = False
        instance.save(
            update_fields=(
                "title",
                "summary",
                "body_markdown",
                "category",
                "reading_minutes",
                "seo_title",
                "seo_description",
                "is_demo",
                "updated_at",
            )
        )
        self._attach_images(instance, body)
        return instance

    @staticmethod
    def _attach_images(article: Article, body: str) -> None:
        public_ids = {match.group(0) for match in NOTE_IMAGE_ID_PATTERN.finditer(body)}
        if public_ids:
            ArticleImage.objects.filter(
                public_id__in=public_ids,
                article__isnull=True,
            ).update(article=article)


class NoteImageUploadRequestSerializer(serializers.Serializer):
    image = serializers.FileField(write_only=True)


class ArticleImageSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    url = serializers.SerializerMethodField()

    @extend_schema_field(serializers.URLField())
    def get_url(self, obj: ArticleImage) -> str:
        request = self.context.get("request")
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url

    class Meta:
        model = ArticleImage
        fields = (
            "id",
            "url",
            "original_filename",
            "content_type",
            "size_bytes",
            "width",
            "height",
        )


class NoteImportRequestSerializer(serializers.Serializer):
    file = serializers.FileField(write_only=True)
    category_slug = serializers.SlugField(max_length=100)
    title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    summary = serializers.CharField(max_length=1000, required=False, allow_blank=True)

    def validate_category_slug(self, value: str) -> str:
        if not Category.objects.filter(slug=value).exists():
            raise serializers.ValidationError("所选分类不存在。")
        return value


class NoteImportErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()
