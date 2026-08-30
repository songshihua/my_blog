from django.contrib import admin

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "external_source",
        "is_published",
        "is_featured",
        "is_demo",
        "sort_order",
        "updated_at",
    )
    list_filter = (
        "category",
        "external_source",
        "is_published",
        "is_featured",
        "is_demo",
        "topics",
    )
    list_editable = ("is_published", "is_featured", "sort_order")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "summary", "problem", "approach")
    filter_horizontal = ("topics",)
