from django.db import migrations


def seed_citizens_charter(apps, schema_editor):
    PublicPage = apps.get_model("content", "PublicPage")
    PublicPage.objects.get_or_create(
        slug="citizens-charter",
        defaults={
            "title": "Citizens Charter",
            "summary": "SDO Sulu service standards and commitments to the public.",
            "body": (
                "The SDO Sulu Citizens Charter presents the office's public services, "
                "requirements, processing steps, responsible offices, and service timelines.\n\n"
                "The official and current Citizens Charter document may be published here "
                "by an authorized administrator through System Administration."
            ),
            "published": True,
        },
    )


def unseed_citizens_charter(apps, schema_editor):
    PublicPage = apps.get_model("content", "PublicPage")
    PublicPage.objects.filter(slug="citizens-charter").delete()


class Migration(migrations.Migration):
    dependencies = [("content", "0007_seed_contact_page")]
    operations = [migrations.RunPython(seed_citizens_charter, unseed_citizens_charter)]
