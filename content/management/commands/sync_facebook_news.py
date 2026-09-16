from datetime import date

from django.core.management.base import BaseCommand, CommandError

from audit.models import AuditLog
from content.facebook_page_sync import FacebookPageSyncError, sync_facebook_news


class Command(BaseCommand):
    help = "Sync non-memorandum News from the configured SDO Facebook Page for 2026–2027."

    def add_arguments(self, parser):
        parser.add_argument("--draft", action="store_true", help="Import matching posts as drafts.")

    def handle(self, *args, **options):
        try:
            summary = sync_facebook_news(
                start_date=date(2026, 1, 1),
                end_date=date(2027, 12, 31),
                publish=not options["draft"],
            )
        except FacebookPageSyncError as exc:
            raise CommandError(str(exc)) from exc
        AuditLog.objects.create(
            action="Scheduled official Facebook News synchronized",
            object_type="System",
            new_value=summary.as_dict(),
        )
        self.stdout.write(self.style.SUCCESS(
            "Facebook News sync complete: "
            f"{summary.imported} imported, {summary.duplicates} duplicates, "
            f"{summary.excluded_memos} memoranda excluded, "
            f"{summary.incomplete} incomplete, {summary.failed} failed."
        ))
