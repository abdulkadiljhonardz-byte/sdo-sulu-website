from django.conf import settings
from django.db import models
from offices.models import TimeStampedModel
class Notification(TimeStampedModel):
    recipient=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="notifications"); title=models.CharField(max_length=200); message=models.TextField(); link=models.CharField(max_length=500,blank=True); read_at=models.DateTimeField(null=True,blank=True)
