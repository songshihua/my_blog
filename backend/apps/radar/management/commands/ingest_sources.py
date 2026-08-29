"""Run configured radar providers as an idempotent one-shot task."""

from contextlib import contextmanager

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

from apps.radar.models import IngestionRun, RadarSource


@contextmanager
def mysql_named_lock(name: str):
    """Fail fast when another ingestion job owns the same MySQL lock."""

    with connection.cursor() as cursor:
        cursor.execute("SELECT GET_LOCK(%s, 0)", [name])
        acquired = cursor.fetchone()[0] == 1
    if not acquired:
        raise CommandError(f"Another ingestion task is already running: {name}")
    try:
        yield
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT RELEASE_LOCK(%s)", [name])


class Command(BaseCommand):
    help = "Run enabled AI radar sources. Provider adapters are opt-in and secret-driven."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source", choices=[choice[0] for choice in RadarSource.SourceType.choices]
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate scheduling and locks without calling external providers.",
        )

    def handle(self, *args, **options):
        sources = RadarSource.objects.filter(is_enabled=True)
        if options["source"]:
            sources = sources.filter(source_type=options["source"])

        with mysql_named_lock("song_blog_ingest_sources"):
            if not sources.exists():
                self.stdout.write("No enabled radar sources; nothing was synchronized.")
                return

            for source in sources:
                run = IngestionRun.objects.create(
                    source=source,
                    status=IngestionRun.Status.RUNNING,
                )
                source.status = RadarSource.Status.RUNNING
                source.save(update_fields=("status", "updated_at"))

                # The first local phase intentionally ships no anonymous sync endpoint
                # and no implicit network calls. Provider adapters are added only after
                # credentials, rate limits, and source-specific tests are configured.
                run.status = IngestionRun.Status.SKIPPED
                run.skipped_count = 1
                run.finished_at = timezone.now()
                run.error_summary = (
                    "Dry run requested."
                    if options["dry_run"]
                    else "Provider adapter is not configured."
                )
                run.save()
                source.status = RadarSource.Status.IDLE
                source.save(update_fields=("status", "updated_at"))
                self.stdout.write(f"Skipped {source.name}: {run.error_summary}")
