import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.models import SiteProfile
from apps.radar.models import RadarItem


@pytest.mark.django_db
def test_only_one_active_profile(profile):
    duplicate = SiteProfile(
        name="另一个用户",
        headline="重复档案",
        affiliation="测试学校",
        research_focus="系统",
    )
    with pytest.raises(ValidationError):
        duplicate.full_clean()


@pytest.mark.django_db
def test_radar_source_and_external_id_are_unique(radar_item, radar_source):
    with pytest.raises(IntegrityError), transaction.atomic():
        RadarItem.objects.create(
            source=radar_source,
            external_id=radar_item.external_id,
            kind=RadarItem.Kind.PAPER,
            title="重复论文",
            original_url="https://arxiv.org/abs/duplicate",
            published_at=timezone.now(),
        )


@pytest.mark.django_db
def test_radar_item_from_another_source_can_reuse_external_id(radar_item):
    assert RadarItem.objects.filter(external_id=radar_item.external_id).count() == 1
