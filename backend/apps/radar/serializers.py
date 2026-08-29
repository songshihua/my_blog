from rest_framework import serializers

from apps.core.serializers import TopicSerializer

from .models import RadarItem, RadarSource


class RadarSourceSerializer(serializers.ModelSerializer):
    source_type_label = serializers.CharField(source="get_source_type_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = RadarSource
        fields = (
            "name",
            "source_type",
            "source_type_label",
            "homepage_url",
            "is_enabled",
            "status",
            "status_label",
            "last_success_at",
        )


class RadarItemListSerializer(serializers.ModelSerializer):
    source = RadarSourceSerializer(read_only=True)
    topics = TopicSerializer(many=True, read_only=True)
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = RadarItem
        fields = (
            "id",
            "source",
            "external_id",
            "kind",
            "kind_label",
            "title",
            "original_url",
            "summary",
            "authors",
            "topics",
            "published_at",
            "fetched_at",
            "relevance_score",
            "is_featured",
            "is_demo",
        )


class RadarItemDetailSerializer(RadarItemListSerializer):
    class Meta(RadarItemListSerializer.Meta):
        fields = RadarItemListSerializer.Meta.fields + ("ai_summary", "metadata")
