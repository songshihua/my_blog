from datetime import timedelta

from django.conf import settings
from django.db.models import Count
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from .briefs import BriefGenerationBusy, RadarBriefGenerator
from .models import IngestionRun, RadarItem, RadarSource
from .providers.base import ProviderResponseError
from .serializers import (
    RadarBriefResponseSerializer,
    RadarItemDetailSerializer,
    RadarItemListSerializer,
    RadarItemSummaryResponseSerializer,
    RadarSourceSerializer,
    RadarStatsSerializer,
    RadarSyncErrorSerializer,
    RadarSyncResponseSerializer,
)
from .services import RadarSyncAlreadyRunning, synchronize_source_types
from .summaries import ItemSummaryBusy, RadarItemSummarizer

BROWSER_SYNC_SOURCE_TYPES = (
    RadarSource.SourceType.ARXIV,
    RadarSource.SourceType.GITHUB,
    RadarSource.SourceType.HUGGINGFACE,
)


class CanUseLocalRadarSync(BasePermission):
    """Permit the mutation only from the trusted local frontend in development."""

    message = "前端同步仅在受信任的本地开发环境中开放。"

    def has_permission(self, request, _view) -> bool:
        if not settings.DEBUG or not settings.RADAR_BROWSER_SYNC_ENABLED:
            return False
        if request.META.get("REMOTE_ADDR") not in {"127.0.0.1", "::1"}:
            return False
        return request.headers.get("Origin", "") in set(settings.CORS_ALLOWED_ORIGINS)


class CanGenerateLocalRadarBrief(BasePermission):
    """Keep the metered generation endpoint private to local development."""

    message = "简报生成仅在受信任的本地开发环境中开放。"

    def has_permission(self, request, _view) -> bool:
        if not settings.DEBUG or not settings.RADAR_BRIEF_GENERATION_ENABLED:
            return False
        if request.META.get("REMOTE_ADDR") not in {"127.0.0.1", "::1"}:
            return False
        return request.headers.get("Origin", "") in set(settings.CORS_ALLOWED_ORIGINS)


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
        queryset = (
            RadarItem.objects.visible()
            .filter(is_demo=False)
            .select_related("source")
            .prefetch_related("topics")
        )
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

    @extend_schema(responses=RadarStatsSerializer)
    def get(self, _request):
        now = timezone.now()
        today = now.date()
        week_start = now - timedelta(days=7)
        items = RadarItem.objects.visible().filter(is_demo=False)
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


class RadarSyncAPIView(APIView):
    """Synchronously refresh the three sources exposed by the local frontend."""

    authentication_classes = ()
    permission_classes = (CanUseLocalRadarSync,)

    @extend_schema(
        request=None,
        responses={
            200: RadarSyncResponseSerializer,
            403: RadarSyncErrorSerializer,
            409: RadarSyncErrorSerializer,
            429: RadarSyncErrorSerializer,
        },
    )
    def post(self, _request):
        cooldown = settings.RADAR_BROWSER_SYNC_COOLDOWN_SECONDS
        latest_attempt = (
            RadarSource.objects.filter(source_type__in=BROWSER_SYNC_SOURCE_TYPES)
            .exclude(last_attempt_at=None)
            .order_by("-last_attempt_at")
            .values_list("last_attempt_at", flat=True)
            .first()
        )
        if latest_attempt is not None:
            elapsed = (timezone.now() - latest_attempt).total_seconds()
            if elapsed < cooldown:
                retry_after = max(1, int(cooldown - elapsed) + 1)
                return Response(
                    {
                        "detail": f"同步操作过于频繁，请在 {retry_after} 秒后重试。",
                        "retry_after": retry_after,
                    },
                    status=429,
                )

        try:
            results = synchronize_source_types(
                BROWSER_SYNC_SOURCE_TYPES,
                limit=min(settings.RADAR_SYNC_LIMIT, 20),
            )
        except RadarSyncAlreadyRunning:
            return Response(
                {"detail": "已有同步任务正在运行，请稍后再试。"},
                status=409,
            )

        serialized_results = [
            {
                "source_type": result.source_type,
                "name": result.name,
                "status": result.outcome.status,
                "inserted": result.outcome.inserted,
                "updated": result.outcome.updated,
                "skipped": result.outcome.skipped,
                "message": result.outcome.message,
            }
            for result in results
        ]
        inserted = sum(result.outcome.inserted for result in results)
        updated = sum(result.outcome.updated for result in results)
        skipped = sum(result.outcome.skipped for result in results)
        succeeded = sum(result.outcome.status == IngestionRun.Status.SUCCESS for result in results)
        failed = sum(result.outcome.status == IngestionRun.Status.FAILED for result in results)
        not_run = len(results) - succeeded - failed

        if succeeded == len(results) and results:
            sync_status = "success"
            message = f"同步完成：新增 {inserted} 条，更新 {updated} 条。"
        elif succeeded:
            sync_status = "partial"
            message = f"同步部分完成：{succeeded} 个成功，{failed + not_run} 个未完成。"
        else:
            sync_status = "error"
            message = "没有数据源同步成功，请检查数据源配置或稍后重试。"

        return Response(
            {
                "status": sync_status,
                "message": message,
                "inserted": inserted,
                "updated": updated,
                "skipped": skipped,
                "results": serialized_results,
            }
        )


class RadarBriefAPIView(APIView):
    """Generate a cached brief from recent, non-demo radar records."""

    authentication_classes = ()
    permission_classes = (CanGenerateLocalRadarBrief,)

    @extend_schema(
        request=None,
        responses={
            200: RadarBriefResponseSerializer,
            403: RadarSyncErrorSerializer,
            409: RadarSyncErrorSerializer,
            502: RadarSyncErrorSerializer,
            503: RadarSyncErrorSerializer,
        },
    )
    def post(self, _request):
        generator = RadarBriefGenerator()
        if error := generator.configuration_error():
            return Response({"detail": error}, status=503)
        try:
            return Response(generator.generate())
        except BriefGenerationBusy as exc:
            return Response({"detail": str(exc)}, status=409)
        except ProviderResponseError as exc:
            return Response({"detail": str(exc)}, status=502)


class RadarItemSummaryAPIView(APIView):
    """Generate once and persist a structured summary for one radar item."""

    authentication_classes = ()
    permission_classes = (CanGenerateLocalRadarBrief,)

    @extend_schema(
        request=None,
        responses={
            200: RadarItemSummaryResponseSerializer,
            403: RadarSyncErrorSerializer,
            404: RadarSyncErrorSerializer,
            409: RadarSyncErrorSerializer,
            502: RadarSyncErrorSerializer,
        },
    )
    def post(self, _request, pk: int):
        try:
            item = (
                RadarItem.objects.visible()
                .filter(is_demo=False)
                .select_related("source")
                .prefetch_related("topics")
                .get(pk=pk)
            )
        except RadarItem.DoesNotExist:
            return Response({"detail": "没有找到这条研究内容。"}, status=404)

        try:
            return Response(RadarItemSummarizer().summarize(item))
        except ItemSummaryBusy as exc:
            return Response({"detail": str(exc)}, status=409)
        except ProviderResponseError as exc:
            return Response({"detail": str(exc)}, status=502)
