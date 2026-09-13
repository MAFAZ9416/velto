"""
Django management command to scan for and recover stale, interrupted conversion jobs.

Usage:
    python backend/manage.py recover_stale_jobs [--timeout-minutes 15]
"""

from django.core.management.base import BaseCommand
from apps.conversions.tasks import recover_stale_jobs_task


class Command(BaseCommand):
    help = "Finds and recovers conversion jobs stuck in active state without recent heartbeat."

    def add_arguments(self, parser):
        parser.add_argument(
            "--timeout-minutes",
            type=int,
            default=15,
            help="Minutes after which an unupdated job is considered stale (default: 15).",
        )

    def handle(self, *args, **options):
        timeout = options["timeout_minutes"]
        self.stdout.write(f"Scanning for stale jobs older than {timeout} minutes...")

        res = recover_stale_jobs_task(timeout_minutes=timeout)
        count = res.get("recovered_count", 0)

        self.stdout.write(
            self.style.SUCCESS(f"Successfully recovered {count} stale conversion job(s).")
        )
