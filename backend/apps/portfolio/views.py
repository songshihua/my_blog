from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Project
from .serializers import ProjectDetailSerializer, ProjectListSerializer


class ProjectViewSet(ReadOnlyModelViewSet):
    permission_classes = (AllowAny,)
    http_method_names = ("get", "head", "options")
    lookup_field = "slug"
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ("category", "is_featured", "topics__slug")
    search_fields = ("title", "subtitle", "summary", "problem", "approach")
    ordering_fields = ("sort_order", "updated_at", "started_at")
    ordering = ("sort_order", "-updated_at")

    def get_queryset(self):
        return Project.objects.filter(is_published=True).prefetch_related("topics")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProjectDetailSerializer
        return ProjectListSerializer
