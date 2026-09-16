import uuid

from django.conf import settings
from django.db import models
from offices.models import Office, TimeStampedModel


def issuance_upload(instance, filename):
    return f"issuances/{uuid.uuid4().hex}.pdf"


def issuance_cover_upload(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"public/issuance-covers/{uuid.uuid4().hex}.{extension}"


class Issuance(TimeStampedModel):
    class Category(models.TextChoices):
        DIVISION_MEMO = "DIVISION_MEMO", "Division Memo"
        OFFICE_MEMO = "OFFICE_MEMO", "Office Memo"
        UNNUMBERED_MEMO = "UNNUMBERED_MEMO", "Unnumbered Memo"
        DIVISION_ADVISORY = "DIVISION_ADVISORY", "Division Advisory"
        DEPED_ORDER = "DEPED_ORDER", "DepEd Order"
        DEPED_MEMORANDUM = "DEPED_MEMORANDUM", "DepEd Memorandum"
        DEPED_ADVISORY = "DEPED_ADVISORY", "DepEd Advisory"
        CIRCULAR = "CIRCULAR", "Circular"
        GUIDELINE = "GUIDELINE", "Guideline"
        POLICY = "POLICY", "Policy"
        NOTICE = "NOTICE", "Official Notice"
        OTHER = "OTHER", "Other"

    category = models.CharField(max_length=30, choices=Category.choices)
    reference_number = models.CharField(max_length=100, unique=True); title = models.CharField(max_length=255)
    description = models.TextField(blank=True); year = models.PositiveIntegerField(); date_issued = models.DateField(null=True, blank=True)
    office = models.ForeignKey(Office, null=True, on_delete=models.SET_NULL)
    cover_image = models.ImageField(upload_to=issuance_cover_upload, blank=True)
    pdf = models.FileField(upload_to=issuance_upload, blank=True)
    source_url = models.URLField(
        "Official source link",
        max_length=1000,
        blank=True,
        help_text="Optional link to the original official Facebook post.",
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_issuances")
    status = models.CharField(max_length=20, default="PUBLISHED"); keywords = models.CharField(max_length=500, blank=True)
    publish_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)
    class Meta: ordering = ["-year", "-date_issued", "-created_at"]
    def __str__(self): return f"{self.reference_number} — {self.title}"


class IssuanceVersion(models.Model):
    issuance = models.ForeignKey(Issuance, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    file = models.FileField(upload_to=issuance_upload)
    reason = models.TextField()
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version_number"]
        constraints = [models.UniqueConstraint(fields=["issuance", "version_number"], name="unique_issuance_version")]
