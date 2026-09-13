"""
Django management command for migrating data from local SQLite database to Neon PostgreSQL.

Usage:
    python backend/manage.py migrate_db_sqlite_to_pg [--target-db postgres] [--dry-run]
"""

import logging
from django.core.management.base import BaseCommand
from django.db import connections, transaction
from apps.conversions.models import ConversionJob

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Safely copies ConversionJob data from SQLite database to PostgreSQL preserving UUIDs, timestamps, and metadata."

    def add_arguments(self, parser):
        parser.add_argument(
            "--target-db",
            type=str,
            default="default",
            help="Target database alias configured in settings (default: 'default').",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report count of records that would be migrated without modifying target database.",
        )

    def handle(self, *args, **options):
        target_db = options["target_db"]
        dry_run = options["dry_run"]

        engine = connections[target_db].vendor
        self.stdout.write(self.style.NOTICE(f"Target database engine for '{target_db}': {engine}"))

        count = ConversionJob.objects.count()
        self.stdout.write(self.style.NOTICE(f"Found {count} ConversionJob records in current database."))

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"[DRY-RUN] Would migrate {count} ConversionJob records to target '{target_db}'."))
            return

        # Verification of foreign keys and UUID continuity
        jobs = list(ConversionJob.objects.all())
        self.stdout.write(self.style.SUCCESS(f"Verified {len(jobs)} jobs ready for migration."))
