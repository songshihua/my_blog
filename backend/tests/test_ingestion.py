import pytest
from django.core.management import call_command

from apps.radar.models import IngestionRun, RadarSource


@pytest.mark.django_db
def test_ingestion_with_no_enabled_sources_is_a_noop(capsys, radar_source):
    call_command("ingest_sources", "--dry-run")

    assert IngestionRun.objects.count() == 0
    assert "No enabled radar sources" in capsys.readouterr().out


@pytest.mark.django_db
def test_unconfigured_provider_is_recorded_as_skipped(radar_source):
    radar_source.is_enabled = True
    radar_source.status = RadarSource.Status.IDLE
    radar_source.save()

    call_command("ingest_sources", "--source", radar_source.source_type, "--dry-run")

    run = IngestionRun.objects.get(source=radar_source)
    assert run.status == IngestionRun.Status.SKIPPED
    assert run.skipped_count == 1
    radar_source.refresh_from_db()
    assert radar_source.status == RadarSource.Status.IDLE
