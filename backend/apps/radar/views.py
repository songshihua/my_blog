from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import RadarItem, RadarSource
from .serializers import (
    RadarItemDetailSerializer,
    RadarItemListSerializer,
    RadarSourceSerializer,
)


class RadarSourceViewSet(ReadOnlyModelViewSet):
    permission_classes = (AllowAny,)
    http_method_names = ("get", "head", "options")
    queryset = RadarSource.objects.all()
    serializer_class = RadarSourceSerializer
    pagination_class = None
    lookup_field = "source_type"


class RadarItemViewSet(ReadOnlyModelViewSet):
    permission_classes = (AllowAny,)
    http_method_names = ("get", "head", "options")
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ("source__source_type", "kind", "topics__slug", "is_featured")
    search_fields = ("title", "summary", "authors")
    ordering_fields = ("published_at", "relevance_score", "fetched_at")
    ordering = ("-published_at",)

    def get_queryset(self):
        queryset = RadarItem.objects.visible().select_related("source").prefetch_related("topics")
        since = self.request.query_params.get("since")
        if since:
            queryset = queryset.filter(published_at__date__gte=since)
        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return RadarItemDetailSerializer
        return RadarItemListSerializer


class RadarStatsAPIView(APIView):
    permission_classes = (AllowAny,)

    def get(self, _request):
        now = timezone.now()
        today = now.date()
        week_start = now - timedelta(days=7)
        items = RadarItem.objects.visible()
        by_kind = dict(items.values_list("kind").annotate(total=Count("id")))
        last_success = (
            RadarSource.objects.exclude(last_success_at=None)
            .order_by("-last_success_at")
            .values_list("last_success_at", flat=True)
            .first()
        )
        return Response(
            {
                "today_count": items.filter(published_at__date=today).count(),
                "week_count": items.filter(published_at__gte=week_start).count(),
                "total_count": items.count(),
                "by_kind": by_kind,
                "last_success_at": last_success,
                "contains_demo_data": items.filter(is_demo=True).exists(),
            }
        )
