"""Explicit response contracts for aggregate public API endpoints."""

from rest_framework import serializers

from apps.blog.serializers import ArticleListSerializer
from apps.portfolio.serializers import ProjectListSerializer
from apps.radar.serializers import RadarItemListSerializer

from .serializers import SiteProfileSerializer


class HomeResponseSerializer(serializers.Serializer):
    profile = SiteProfileSerializer(allow_null=True)
    featured_projects = ProjectListSerializer(many=True)
    recent_articles = ArticleListSerializer(many=True)
    radar_items = RadarItemListSerializer(many=True)
    demo_notice = serializers.CharField()
