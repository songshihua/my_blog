"""Versioned public API routes."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.blog.views import ArticleViewSet
from apps.core.views import HomeAPIView, ProfileAPIView, TopicViewSet
from apps.portfolio.views import ProjectViewSet
from apps.radar.views import (
    RadarBriefAPIView,
    RadarItemSummaryAPIView,
    RadarItemViewSet,
    RadarSourceViewSet,
    RadarStatsAPIView,
    RadarSyncAPIView,
)

router = DefaultRouter()
router.register("topics", TopicViewSet, basename="topic")
router.register("projects", ProjectViewSet, basename="project")
router.register("articles", ArticleViewSet, basename="article")
router.register("radar/items", RadarItemViewSet, basename="radar-item")
router.register("radar/sources", RadarSourceViewSet, basename="radar-source")

urlpatterns = [
    path(
        "radar/items/<int:pk>/summary/",
        RadarItemSummaryAPIView.as_view(),
        name="radar-item-summary",
    ),
    path("radar/brief/", RadarBriefAPIView.as_view(), name="radar-brief"),
    path("radar/sync/", RadarSyncAPIView.as_view(), name="radar-sync"),
    path("", include(router.urls)),
    path("home/", HomeAPIView.as_view(), name="home"),
    path("profile/", ProfileAPIView.as_view(), name="profile"),
    path("radar/stats/", RadarStatsAPIView.as_view(), name="radar-stats"),
]
