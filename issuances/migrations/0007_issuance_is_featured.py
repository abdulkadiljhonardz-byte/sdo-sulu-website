from django.db import migrations, models


def feature_latest_memo(apps, schema_editor):
    Issuance = apps.get_model("issuances", "Issuance")
    latest = Issuance.objects.filter(
        status="PUBLISHED",
        archived=False,
        category="DIVISION_MEMO",
    ).order_by("-year", "-date_issued", "-created_at").first()
    if latest:
        latest.is_featured = True
        latest.save(update_fields=["is_featured"])


class Migration(migrations.Migration):
    dependencies = [("issuances", "0006_issuance_external_source")]

    operations = [
        migrations.AddField(
            model_name="issuance",
            name="is_featured",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(feature_latest_memo, migrations.RunPython.noop),
    ]
