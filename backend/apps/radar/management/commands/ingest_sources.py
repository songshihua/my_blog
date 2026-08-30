"""Run configured radar providers as an idempotent one-shot task."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.radar.models import RadarSource
from apps.radar.services import RadarSyncAlreadyRunning, synchronize_source_types


class Command(BaseCommand):
    help = "Run enabled AI radar sources. Provider adapters are opt-in and secret-driven."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source", choices=[choice[0] for choice in RadarSource.SourceType.choices]
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=settings.RADAR_SYNC_LIMIT,
            help="Maximum records per provider (1-100).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate scheduling and locks without calling external providers.",
        )

    def handle(self, *args, **options):
        limit = max(1, min(options["limit"], 100))
        source_types = [options["source"]] if options["source"] else None
        try:
            results = synchronize_source_types(
                source_types,
                limit=limit,
                dry_run=options["dry_run"],
            )
        except RadarSyncAlreadyRunning as exc:
            raise CommandError(str(exc)) from exc

        if not results:
            self.stdout.write("No enabled radar sources; nothing was synchronized.")
            return

        failed_sources: list[str] = []
        for result in results:
            outcome = result.outcome
            self.stdout.write(
                f"{result.name}: {outcome.status} "
                f"(inserted={outcome.inserted}, updated={outcome.updated}, "
                f"skipped={outcome.skipped})"
            )
            if outcome.status == "failed":
                failed_sources.append(result.name)

        if failed_sources:
            raise CommandError(f"Synchronization failed: {', '.join(failed_sources)}")
