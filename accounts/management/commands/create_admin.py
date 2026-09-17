import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Create an initial superuser from explicitly configured environment variables."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_INITIAL_ADMIN_USERNAME", "").strip()
        email = os.environ.get("DJANGO_INITIAL_ADMIN_EMAIL", "").strip()
        password = os.environ.get("DJANGO_INITIAL_ADMIN_PASSWORD", "")

        if not all((username, email, password)):
            self.stdout.write("Initial admin variables are not configured; skipped.")
            return

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"Created initial superuser: {username}"))
        else:
            self.stdout.write(f"Initial superuser {username} already exists; skipped.")
