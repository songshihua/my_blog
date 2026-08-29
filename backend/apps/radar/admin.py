from django.contrib import admin

from .models import IngestionRun, RadarItem, RadarSource


@admin.register(RadarSource)
class RadarSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "source_type", "is_enabled", "status", "last_success_at")
    list_filter = ("is_enabled", "status", "source_type")


@admin.register(RadarItem)
class RadarItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "source",
        "kind",
        "published_at",
        "is_featured",
        "is_visible",
        "is_demo",
    )
    list_filter = ("source", "kind", "is_featured", "is_visible", "is_demo", "topics")
    search_fields = ("title", "summary", "external_id")
    filter_horizontal = ("topics",)


@admin.register(IngestionRun)
class IngestionRunAdmin(admin.ModelAdmin):
    list_display = (
        "source",
        "status",
        "started_at",
        "finished_at",
        "inserted_count",
        "updated_count",
        "error_count",
    )
    list_filter = ("status", "source")
    readonly_fields = (
        "source",
        "status",
        "started_at",
        "finished_at",
        "inserted_count",
        "updated_count",
        "skipped_count",
        "error_count",
        "error_summary",
        "created_at",
        "updated_at",
    )
