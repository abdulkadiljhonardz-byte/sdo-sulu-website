from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from audit.models import AuditLog
from content.models import Announcement, Download, News
from issuances.models import Issuance
from core.models import AnalyticsEvent


class Command(BaseCommand):
    help = "Archive published portal records whose configured expiration time has passed."

    def handle(self, *args, **options):
        now = timezone.now()
        counts = {
            "news": News.objects.filter(expires_at__lte=now, archived=False).update(archived=True, is_published=False),
            "announcements": Announcement.objects.filter(expires_at__lte=now, archived=False).update(archived=True, is_published=False),
            "downloads": Download.objects.filter(expires_at__lte=now, archived=False).update(archived=True, published=False),
            "issuances": Issuance.objects.filter(expires_at__lte=now, archived=False).update(archived=True, status="ARCHIVED"),
            "analytics_pruned": AnalyticsEvent.objects.filter(created_at__lt=now - timedelta(days=730)).delete()[0],
        }
        total = sum(counts.values())
        if total:
            AuditLog.objects.create(action="Expired publications archived", object_type="System", new_value=counts)
        self.stdout.write(self.style.SUCCESS(f"Archived {total} expired record(s)."))
