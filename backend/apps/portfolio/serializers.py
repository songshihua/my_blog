from rest_framework import serializers

from apps.core.serializers import TopicSerializer

from .models import Project


class ProjectListSerializer(serializers.ModelSerializer):
    topics = TopicSerializer(many=True, read_only=True)
    category_label = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Project
        fields = (
            "title",
            "slug",
            "subtitle",
            "category",
            "category_label",
            "summary",
            "topics",
            "repository_url",
            "demo_url",
            "is_featured",
            "is_demo",
            "updated_at",
        )


class ProjectDetailSerializer(ProjectListSerializer):
    class Meta(ProjectListSerializer.Meta):
        fields = ProjectListSerializer.Meta.fields + (
            "problem",
            "approach",
            "contribution",
            "outcome",
            "started_at",
            "ended_at",
        )
