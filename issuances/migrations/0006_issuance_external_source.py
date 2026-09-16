from django.db import migrations, models

import issuances.models


class Migration(migrations.Migration):
    dependencies = [("issuances", "0005_issuance_cover_image")]

    operations = [
        migrations.AddField(
            model_name="issuance",
            name="source_url",
            field=models.URLField(
                blank=True,
                help_text="Optional link to the original official Facebook post.",
                max_length=1000,
                verbose_name="Official source link",
            ),
        ),
        migrations.AlterField(
            model_name="issuance",
            name="date_issued",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="issuance",
            name="pdf",
            field=models.FileField(blank=True, upload_to=issuances.models.issuance_upload),
        ),
        migrations.AlterModelOptions(
            name="issuance",
            options={"ordering": ["-year", "-date_issued", "-created_at"]},
        ),
    ]
