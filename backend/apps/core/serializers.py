from rest_framework import serializers

from .models import SiteProfile, Topic


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ("name", "slug", "description", "color")


class SiteProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteProfile
        fields = (
            "name",
            "english_name",
            "headline",
            "bio",
            "affiliation",
            "role",
            "research_focus",
            "github_url",
            "email",
            "seo_description",
            "updated_at",
        )
