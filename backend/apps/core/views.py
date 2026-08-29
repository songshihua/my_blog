from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.blog.models import Article
from apps.blog.serializers import ArticleListSerializer
from apps.portfolio.models import Project
from apps.portfolio.serializers import ProjectListSerializer
from apps.radar.models import RadarItem
from apps.radar.serializers import RadarItemListSerializer

from .models import SiteProfile, Topic
from .serializers import SiteProfileSerializer, TopicSerializer


class PublicReadOnlyMixin:
    permission_classes = (AllowAny,)
    http_method_names = ("get", "head", "options")


class TopicViewSet(PublicReadOnlyMixin, ReadOnlyModelViewSet):
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer
    pagination_class = None
    search_fields = ("name", "description")


class ProfileAPIView(APIView):
    permission_classes = (AllowAny,)

    def get(self, _request):
        profile = SiteProfile.objects.filter(is_active=True).first()
        if profile is None:
            return Response({"detail": "Profile is not configured."}, status=404)
        return Response(SiteProfileSerializer(profile).data)


class HomeAPIView(APIView):
    """Aggregate the first viewport into one cache-friendly request."""

    permission_classes = (AllowAny,)

    def get(self, _request):
        profile = SiteProfile.objects.filter(is_active=True).first()
        projects = Project.objects.filter(is_published=True, is_featured=True)[:3]
        articles = Article.objects.published()[:3]
        radar_items = RadarItem.objects.visible()[:5]
        return Response(
            {
                "profile": SiteProfileSerializer(profile).data if profile else None,
                "featured_projects": ProjectListSerializer(projects, many=True).data,
                "recent_articles": ArticleListSerializer(articles, many=True).data,
                "radar_items": RadarItemListSerializer(radar_items, many=True).data,
                "demo_notice": (
                    "Records marked is_demo are interface samples and are not claimed results."
                ),
            }
        )
