from django.conf import settings
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from .importers import DuplicateNoteError, NoteImportError, import_note
from .models import MAX_CATEGORY_DEPTH, Article, ArticleSourceFile, Category
from .permissions import CanUseLocalNoteImport
from .serializers import (
    ArticleDetailSerializer,
    ArticleListSerializer,
    CategoryCreateRequestSerializer,
    CategorySerializer,
    NoteImportErrorSerializer,
    NoteImportRequestSerializer,
    NoteTreeResponseSerializer,
)


class ArticleViewSet(ReadOnlyModelViewSet):
    permission_classes = (AllowAny,)
    http_method_names = ("get", "post", "delete", "head", "options")
    lookup_field = "slug"
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ("category__slug", "topics__slug", "is_featured")
    search_fields = ("title", "summary", "body_markdown")
    ordering_fields = ("published_at", "updated_at", "reading_minutes")
    ordering = ("-published_at",)

    def get_queryset(self):
        return (
            Article.objects.published()
            .select_related("category", "category__parent", "source_file")
            .prefetch_related("topics")
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ArticleDetailSerializer
        return ArticleListSerializer

    @extend_schema(responses=NoteTreeResponseSerializer)
    @action(detail=False, methods=("get",), pagination_class=None)
    def tree(self, request):
        categories = Category.objects.select_related("parent").all()
        articles = self.get_queryset()
        return Response(
            {
                "categories": CategorySerializer(
                    categories, many=True, context={"request": request}
                ).data,
                "articles": ArticleListSerializer(
                    articles, many=True, context={"request": request}
                ).data,
                "import_enabled": bool(settings.DEBUG and settings.NOTE_BROWSER_IMPORT_ENABLED),
                "max_category_depth": MAX_CATEGORY_DEPTH,
            }
        )

    @extend_schema(
        request=CategoryCreateRequestSerializer,
        responses={
            201: CategorySerializer,
            400: NoteImportErrorSerializer,
            403: NoteImportErrorSerializer,
        },
    )
    @action(
        detail=False,
        methods=("post",),
        url_path="categories",
        url_name="categories",
        authentication_classes=(),
        permission_classes=(CanUseLocalNoteImport,),
    )
    def create_category(self, request):
        serializer = CategoryCreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        return Response(
            CategorySerializer(category, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=None,
        responses={
            204: None,
            403: NoteImportErrorSerializer,
            409: NoteImportErrorSerializer,
        },
    )
    @action(
        detail=False,
        methods=("delete",),
        url_path=r"categories/(?P<category_slug>[-a-zA-Z0-9_]+)",
        url_name="category-detail",
        authentication_classes=(),
        permission_classes=(CanUseLocalNoteImport,),
    )
    def delete_category(self, _request, category_slug=None):
        category = get_object_or_404(Category, slug=category_slug)
        if category.children.exists():
            return Response(
                {"detail": "该目录仍包含子目录，请先逐级删除子目录。"},
                status=status.HTTP_409_CONFLICT,
            )
        if category.articles.exists():
            return Response(
                {"detail": "该目录仍包含文章，请先删除或移动目录内文章。"},
                status=status.HTTP_409_CONFLICT,
            )
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        request=NoteImportRequestSerializer,
        responses={
            201: ArticleDetailSerializer,
            400: NoteImportErrorSerializer,
            403: NoteImportErrorSerializer,
            409: NoteImportErrorSerializer,
        },
    )
    @action(
        detail=False,
        methods=("post",),
        url_path="import",
        authentication_classes=(),
        permission_classes=(CanUseLocalNoteImport,),
        parser_classes=(MultiPartParser, FormParser),
    )
    def import_file(self, request):
        serializer = NoteImportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = get_object_or_404(
            Category,
            slug=serializer.validated_data["category_slug"],
        )
        try:
            article = import_note(
                serializer.validated_data["file"],
                category=category,
                title=serializer.validated_data.get("title", ""),
                summary=serializer.validated_data.get("summary", ""),
            )
        except DuplicateNoteError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except NoteImportError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            ArticleDetailSerializer(article, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(responses={(200, "application/octet-stream"): bytes})
    @action(detail=True, methods=("get",), url_path="source-file")
    def source_file(self, request, slug=None):
        article = self.get_object()
        source = get_object_or_404(ArticleSourceFile, article=article)
        response = FileResponse(
            source.file.open("rb"),
            as_attachment=True,
            filename=source.original_filename,
            content_type=source.content_type or "application/octet-stream",
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        return response

    @extend_schema(
        request=None,
        responses={204: None, 403: NoteImportErrorSerializer},
    )
    @action(
        detail=True,
        methods=("delete",),
        url_path="manage",
        url_name="manage",
        authentication_classes=(),
        permission_classes=(CanUseLocalNoteImport,),
    )
    def delete_note(self, _request, slug=None):
        article = self.get_object()
        article.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=("get",), pagination_class=None)
    def related(self, _request, slug=None):
        article = self.get_object()
        topic_ids = article.topics.values_list("id", flat=True)
        related = (
            self.get_queryset().filter(topics__in=topic_ids).exclude(pk=article.pk).distinct()[:3]
        )
        return Response(ArticleListSerializer(related, many=True).data)
