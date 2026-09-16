from django.db import models
from offices.models import TimeStampedModel
class Feedback(TimeStampedModel):
    rating=models.PositiveSmallIntegerField(null=True,blank=True); message=models.TextField(); anonymous=models.BooleanField(default=False); email=models.EmailField(blank=True)
class Complaint(TimeStampedModel):
    reference_number=models.CharField(max_length=40,unique=True); subject=models.CharField(max_length=255); details=models.TextField(); email=models.EmailField(blank=True); status=models.CharField(max_length=20,default="OPEN")
