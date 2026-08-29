from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Article
from .serializers import ArticleDetailSerializer, ArticleListSerializer


class ArticleViewSet(ReadOnlyModelViewSet):
    permission_classes = (AllowAny,)
    http_method_names = ("get", "head", "options")
    lookup_field = "slug"
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ("category__slug", "topics__slug", "is_featured")
    search_fields = ("title", "summary", "body_markdown")
    ordering_fields = ("published_at", "updated_at", "reading_minutes")
    ordering = ("-published_at",)

    def get_queryset(self):
        return Article.objects.published().select_related("category").prefetch_related("topics")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ArticleDetailSerializer
        return ArticleListSerializer

    @action(detail=True, methods=("get",), pagination_class=None)
    def related(self, _request, slug=None):
        article = self.get_object()
        topic_ids = article.topics.values_list("id", flat=True)
        related = (
            self.get_queryset()
            .filter(topics__in=topic_ids)
            .exclude(pk=article.pk)
            .distinct()[:3]
        )
        return Response(ArticleListSerializer(related, many=True).data)
