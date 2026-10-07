from django.db import migrations, models

import content.models


class Migration(migrations.Migration):
    dependencies = [("content", "0009_add_public_page_document")]

    operations = [
        migrations.CreateModel(
            name="HomepageSlide",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=180)),
                ("caption", models.TextField(blank=True)),
                ("image", models.ImageField(upload_to=content.models.public_upload)),
                (
                    "link_label",
                    models.CharField(
                        blank=True,
                        help_text="Optional button text, for example Learn more.",
                        max_length=60,
                    ),
                ),
                (
                    "link_url",
                    models.URLField(
                        blank=True,
                        help_text="Optional page opened by the slide button.",
                        max_length=1000,
                    ),
                ),
                (
                    "sort_order",
                    models.PositiveSmallIntegerField(
                        default=0, help_text="Lower numbers appear first."
                    ),
                ),
                ("active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["sort_order", "-updated_at"]},
        )
    ]
