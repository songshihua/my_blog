from django.contrib import admin

from .models import Article, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "sort_order")
    list_editable = ("sort_order",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "status",
        "published_at",
        "is_featured",
        "is_demo",
        "updated_at",
    )
    list_filter = ("status", "category", "topics", "is_featured", "is_demo")
    list_editable = ("status", "is_featured")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "summary", "body_markdown")
    filter_horizontal = ("topics",)
