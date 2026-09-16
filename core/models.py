from django.conf import settings
from django.db import models


class AnalyticsEvent(models.Model):
    class Type(models.TextChoices):
        NEWS_VIEW = "NEWS_VIEW", "News view"
        ISSUANCE_DOWNLOAD = "ISSUANCE_DOWNLOAD", "Issuance download"
        RESOURCE_DOWNLOAD = "RESOURCE_DOWNLOAD", "Resource download"
        SEARCH = "SEARCH", "Portal search"
        DIRECTORY_VISIT = "DIRECTORY_VISIT", "School-directory visit"
        SCHOOL_VIEW = "SCHOOL_VIEW", "School profile view"

    event_type = models.CharField(max_length=30, choices=Type.choices, db_index=True)
    path = models.CharField(max_length=500, blank=True)
    object_type = models.CharField(max_length=50, blank=True, db_index=True)
    object_id = models.CharField(max_length=64, blank=True, db_index=True)
    query = models.CharField(max_length=255, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
