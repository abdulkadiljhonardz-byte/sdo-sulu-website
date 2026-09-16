from django.db import models
from offices.models import Office, TimeStampedModel
class Event(TimeStampedModel):
    title=models.CharField(max_length=255); description=models.TextField(blank=True); start=models.DateTimeField(); end=models.DateTimeField(null=True,blank=True); location=models.CharField(max_length=255,blank=True); organizer=models.CharField(max_length=255,blank=True); category=models.CharField(max_length=100,blank=True); office=models.ForeignKey(Office,null=True,blank=True,on_delete=models.SET_NULL)
    def __str__(self): return self.title
