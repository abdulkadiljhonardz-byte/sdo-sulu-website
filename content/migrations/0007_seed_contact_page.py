from django.db import migrations


def seed_contact_page(apps, schema_editor):
    PublicPage = apps.get_model("content", "PublicPage")
    PublicPage.objects.get_or_create(
        slug="contact",
        defaults={
            "title": "Contact SDO Sulu",
            "summary": "Use the official contact channels below for division inquiries.",
            "body": "Our office is available during regular government working hours. Please use the appropriate official channel below and avoid sending confidential personal information through public messaging services.",
            "published": True,
        },
    )


def unseed_contact_page(apps, schema_editor):
    PublicPage = apps.get_model("content", "PublicPage")
    PublicPage.objects.filter(slug="contact").delete()


class Migration(migrations.Migration):
    dependencies = [("content", "0006_news_facebook_post_id")]
    operations = [migrations.RunPython(seed_contact_page, unseed_contact_page)]
