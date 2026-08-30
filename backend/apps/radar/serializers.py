from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.core.serializers import TopicSerializer

from .models import RadarItem, RadarSource
from .providers import provider_configuration_error


class RepositoryMetricsSerializer(serializers.Serializer):
    stars = serializers.IntegerField(min_value=0)
    forks = serializers.IntegerField(min_value=0)
    language = serializers.CharField(allow_blank=True)


class RadarSourceSerializer(serializers.ModelSerializer):
    source_type_label = serializers.CharField(source="get_source_type_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    is_configured = serializers.SerializerMethodField()

    def get_is_configured(self, obj: RadarSource) -> bool:
        return provider_configuration_error(obj.source_type) is None

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
            "is_configured",
            "last_attempt_at",
            "last_success_at",
            "last_error_at",
            "last_item_count",
        )


class RadarItemListSerializer(serializers.ModelSerializer):
    source = RadarSourceSerializer(read_only=True)
    topics = TopicSerializer(many=True, read_only=True)
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    repository_metrics = serializers.SerializerMethodField()

    @extend_schema_field(RepositoryMetricsSerializer(allow_null=True))
    def get_repository_metrics(self, obj: RadarItem) -> dict[str, object] | None:
        if obj.source.source_type != RadarSource.SourceType.GITHUB:
            return None
        metadata = obj.metadata if isinstance(obj.metadata, dict) else {}

        def safe_count(value: object) -> int:
            try:
                return max(int(value or 0), 0)
            except (TypeError, ValueError):
                return 0

        language = str(metadata.get("language") or "").strip()[:80]
        return {
            "stars": safe_count(metadata.get("stars")),
            "forks": safe_count(metadata.get("forks")),
            "language": language,
        }

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
            "ai_summary",
            "repository_metrics",
        )


class RadarItemDetailSerializer(RadarItemListSerializer):
    class Meta(RadarItemListSerializer.Meta):
        fields = RadarItemListSerializer.Meta.fields + ("metadata",)


class RadarStatsSerializer(serializers.Serializer):
    today_count = serializers.IntegerField(min_value=0)
    week_count = serializers.IntegerField(min_value=0)
    total_count = serializers.IntegerField(min_value=0)
    by_kind = serializers.DictField(child=serializers.IntegerField(min_value=0))
    last_success_at = serializers.DateTimeField(allow_null=True)
    contains_demo_data = serializers.BooleanField()


class RadarSyncSourceResultSerializer(serializers.Serializer):
    source_type = serializers.CharField()
    name = serializers.CharField()
    status = serializers.ChoiceField(choices=("success", "failed", "skipped"))
    inserted = serializers.IntegerField(min_value=0)
    updated = serializers.IntegerField(min_value=0)
    skipped = serializers.IntegerField(min_value=0)
    message = serializers.CharField(allow_blank=True)


class RadarSyncResponseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=("success", "partial", "error"))
    message = serializers.CharField()
    inserted = serializers.IntegerField(min_value=0)
    updated = serializers.IntegerField(min_value=0)
    skipped = serializers.IntegerField(min_value=0)
    results = RadarSyncSourceResultSerializer(many=True)


class RadarSyncErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()
    retry_after = serializers.IntegerField(min_value=1, required=False)
