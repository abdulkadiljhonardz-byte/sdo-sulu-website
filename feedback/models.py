from django.db import models
from offices.models import TimeStampedModel
class Feedback(TimeStampedModel):
    rating=models.PositiveSmallIntegerField(null=True,blank=True); message=models.TextField(); anonymous=models.BooleanField(default=False); email=models.EmailField(blank=True)
class Complaint(TimeStampedModel):
    reference_number=models.CharField(max_length=40,unique=True); subject=models.CharField(max_length=255); details=models.TextField(); email=models.EmailField(blank=True); status=models.CharField(max_length=20,default="OPEN")


class ContactInquiry(TimeStampedModel):
    class Status(models.TextChoices):
        NEW = "NEW", "New"
        IN_REVIEW = "IN_REVIEW", "In review"
        RESOLVED = "RESOLVED", "Resolved"

    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    address = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    ip_address = models.GenericIPAddressField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Inquiry from {self.name}"
