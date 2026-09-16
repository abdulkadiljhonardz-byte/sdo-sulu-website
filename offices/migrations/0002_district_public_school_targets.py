from django.db import migrations, models


DISTRICT_TARGETS = (
    ("Indanan", "Indanan", 39),
    ("Jolo I", "Jolo", 10),
    ("Jolo II", "Jolo", 8),
    ("Jolo III", "Jolo", 7),
    ("Jolo IV", "Jolo", 14),
    ("Maimbung", "Maimbung", 20),
    ("Pangutaran", "Pangutaran", 34),
    ("Parang", "Parang", 31),
    ("Patikul", "Patikul", 34),
    ("Talipao", "Talipao", 44),
    ("Tongkil / Banguingui", "Banguingui", 18),
    ("Laminusa", "Laminusa", 18),
    ("Lugus", "Lugus", 18),
    ("Luuk (Kalinggalan Caluang)", "Luuk / Kalinggalan Caluang", 46),
    ("Panamao", "Panamao", 29),
    ("Pata", "Pata", 15),
    ("Siasi I", "Siasi", 17),
    ("Siasi II", "Siasi", 16),
    ("Sibaud", "Sibaud", 23),
    ("Tapul", "Tapul", 16),
)


def seed_district_targets(apps, schema_editor):
    District = apps.get_model("offices", "District")
    for name, municipality, target in DISTRICT_TARGETS:
        District.objects.update_or_create(
            name=name,
            defaults={
                "municipality": municipality,
                "public_school_target": target,
                "active": True,
            },
        )


def clear_district_targets(apps, schema_editor):
    District = apps.get_model("offices", "District")
    District.objects.filter(name__in=[item[0] for item in DISTRICT_TARGETS]).update(
        public_school_target=0
    )


class Migration(migrations.Migration):
    dependencies = [("offices", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="district",
            name="public_school_target",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Official target number of public schools for this district.",
            ),
        ),
        migrations.RunPython(seed_district_targets, clear_district_targets),
    ]
