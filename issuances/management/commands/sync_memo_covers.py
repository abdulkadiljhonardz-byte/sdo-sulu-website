from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from content.facebook_import import FacebookImportError, import_facebook_post
from issuances.models import Issuance


class Command(BaseCommand):
    help = "Download missing memorandum cover images from verified Facebook sources."

    def handle(self, *args, **options):
        records = Issuance.objects.filter(
            category=Issuance.Category.DIVISION_MEMO,
            source_url__gt="",
            cover_image="",
        ).order_by("reference_number")
        imported = 0
        failed = []
        for item in records:
            try:
                post = import_facebook_post(item.source_url, require_text=False)
                item.cover_image.save(
                    post.image_name,
                    ContentFile(post.image_bytes),
                    save=True,
                )
                imported += 1
                self.stdout.write(f"Imported cover: {item.reference_number}")
            except FacebookImportError as exc:
                failed.append((item.reference_number, str(exc)))
                self.stderr.write(f"Skipped {item.reference_number}: {exc}")
        self.stdout.write(
            self.style.SUCCESS(
                f"Cover sync complete: {imported} imported, {len(failed)} failed."
            )
        )
