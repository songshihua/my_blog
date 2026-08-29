from django.contrib import admin

from .models import SiteProfile, Topic


@admin.register(SiteProfile)
class SiteProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "affiliation", "role", "is_active", "updated_at")
    list_filter = ("is_active",)


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "sort_order", "updated_at")
    list_editable = ("sort_order",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "description")
