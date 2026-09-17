"""Idempotently seed the verified NID Sulu school ID/name directory."""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from schools.models import School


class Command(BaseCommand):
    help = "Seed the official NID Sulu school ID/name directory."

    def handle(self, *args, **options):
        source = Path(settings.BASE_DIR) / "deployment" / "seed_sulu_schools.json"
        if not source.exists():
            raise CommandError("NID Sulu school seed file is missing.")
        records = json.loads(source.read_text(encoding="utf-8"))
        if len(records) != 457:
            raise CommandError("NID Sulu school seed must contain exactly 457 records.")

        created = updated = 0
        for record in records:
            school, was_created = School.objects.get_or_create(
                school_id=record["school_id"],
                defaults={
                    "name": record["name"],
                    "district": None,
                    "classification": "PUBLIC",
                    "status": "ACTIVE",
                },
            )
            if was_created:
                created += 1
            else:
                # Preserve district assignments and other information added by staff.
                changed_fields = []
                for field, value in {
                    "name": record["name"],
                    "classification": "PUBLIC",
                    "status": "ACTIVE",
                }.items():
                    if getattr(school, field) != value:
                        setattr(school, field, value)
                        changed_fields.append(field)
                if changed_fields:
                    school.save(update_fields=[*changed_fields, "updated_at"])
                    updated += 1
        self.stdout.write(self.style.SUCCESS(f"NID Sulu schools ready: {created} created, {updated} updated."))
