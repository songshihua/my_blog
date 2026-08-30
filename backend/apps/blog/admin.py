from django.contrib import admin

from .models import Article, ArticleSourceFile, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "slug", "sort_order")
    list_filter = ("parent",)
    list_editable = ("sort_order",)
    prepopulated_fields = {"slug": ("name",)}


class ArticleSourceFileInline(admin.StackedInline):
    model = ArticleSourceFile
    extra = 0
    can_delete = True
    readonly_fields = (
        "original_filename",
        "source_format",
        "content_type",
        "size_bytes",
        "sha256",
        "outline",
        "extracted_at",
        "created_at",
        "updated_at",
    )


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
    inlines = (ArticleSourceFileInline,)
