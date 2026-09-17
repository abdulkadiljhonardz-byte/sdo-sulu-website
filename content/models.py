import uuid

from django.db import models
from offices.models import Office, TimeStampedModel


def public_upload(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"public/{uuid.uuid4().hex}.{extension}"

class Publication(TimeStampedModel):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    body = models.TextField()
    category = models.CharField(max_length=100, blank=True)
    cover_image = models.ImageField(upload_to=public_upload, blank=True)
    source_url = models.URLField(
        "Facebook source link",
        max_length=1000,
        blank=True,
        help_text="Optional link to the original Facebook post.",
    )
    source_imported_at = models.DateTimeField(null=True, blank=True, editable=False)
    office = models.ForeignKey(Office, null=True, blank=True, on_delete=models.SET_NULL)
    author = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL)
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)
    class Meta: abstract = True; ordering = ["-published_at"]
class News(Publication):
    facebook_post_id = models.CharField(
        max_length=160,
        null=True,
        blank=True,
        unique=True,
        editable=False,
    )

    def __str__(self): return self.title
class Announcement(Publication):
    important = models.BooleanField(default=False)
    def __str__(self): return self.title
class Download(TimeStampedModel):
    title = models.CharField(max_length=255); category = models.CharField(max_length=100)
    file = models.FileField(upload_to=public_upload); description = models.TextField(blank=True)
    office = models.ForeignKey(Office, null=True, blank=True, on_delete=models.SET_NULL)
    published = models.BooleanField(default=True)
    publish_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    archived = models.BooleanField(default=False)
    def __str__(self): return self.title
class SiteSetting(TimeStampedModel):
    key = models.CharField(max_length=100, unique=True); value = models.TextField(blank=True)


class PublicPage(TimeStampedModel):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True)
    body = models.TextField()
    image = models.ImageField(upload_to=public_upload, blank=True)
    document = models.FileField(upload_to=public_upload, blank=True)
    published = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title
