from rest_framework import serializers

from apps.core.serializers import TopicSerializer

from .models import Article, Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("name", "slug", "description")


class ArticleListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    topics = TopicSerializer(many=True, read_only=True)

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
        )


class ArticleDetailSerializer(ArticleListSerializer):
    class Meta(ArticleListSerializer.Meta):
        fields = ArticleListSerializer.Meta.fields + (
            "body_markdown",
            "repository_url",
            "seo_title",
            "seo_description",
        )
