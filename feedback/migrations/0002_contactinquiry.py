from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("feedback", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="ContactInquiry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=120)),
                ("email", models.EmailField(max_length=254)),
                ("phone", models.CharField(max_length=30)),
                ("address", models.CharField(blank=True, max_length=255)),
                ("message", models.TextField()),
                ("status", models.CharField(choices=[("NEW", "New"), ("IN_REVIEW", "In review"), ("RESOLVED", "Resolved")], default="NEW", max_length=20)),
                ("ip_address", models.GenericIPAddressField(blank=True, editable=False, null=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
