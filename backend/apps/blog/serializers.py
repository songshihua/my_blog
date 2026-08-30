from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.db.models import Max
from django.utils.text import slugify
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.reverse import reverse

from apps.core.serializers import TopicSerializer

from .importers import extract_outline
from .models import MAX_CATEGORY_DEPTH, Article, ArticleSourceFile, Category


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

    @extend_schema_field(serializers.CharField())
    def get_download_url(self, obj: ArticleSourceFile) -> str:
        return reverse(
            "article-source-file",
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
        source = getattr(obj, "source_file", None)
        if source is not None and isinstance(source.outline, list):
            return source.outline
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
    max_category_depth = serializers.IntegerField()


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
