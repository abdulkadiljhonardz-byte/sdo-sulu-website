from pathlib import Path
import shutil

from django.conf import settings
from django.core.management import BaseCommand, call_command

from content.models import News
from issuances.models import Issuance


class Command(BaseCommand):
    help = "Load the initial public news, memoranda, and their public images."

    def handle(self, *args, **options):
        deployment_dir = Path(settings.BASE_DIR) / "deployment"

        if not News.objects.exists():
            call_command("loaddata", deployment_dir / "seed_news.json", verbosity=0)
            self.stdout.write(self.style.SUCCESS("Loaded initial news."))
        else:
            self.stdout.write("News already exists; seed skipped.")

        if not Issuance.objects.exists():
            call_command(
                "loaddata", deployment_dir / "seed_issuances.json", verbosity=0
            )
            self.stdout.write(self.style.SUCCESS("Loaded initial memoranda."))
        else:
            self.stdout.write("Issuances already exist; seed skipped.")

        source_root = deployment_dir / "seed_media"
        copied = 0
        for source in source_root.rglob("*"):
            if not source.is_file():
                continue
            destination = Path(settings.MEDIA_ROOT) / source.relative_to(source_root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                shutil.copy2(source, destination)
                copied += 1

        self.stdout.write(f"Restored {copied} missing public media file(s).")
