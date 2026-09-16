from django.db import models
from offices.models import Office, TimeStampedModel
class Vacancy(TimeStampedModel):
    position=models.CharField(max_length=255); office=models.ForeignKey(Office,on_delete=models.PROTECT); employment_type=models.CharField(max_length=100); salary_grade=models.CharField(max_length=50,blank=True); qualification=models.TextField(); education=models.TextField(blank=True); experience=models.TextField(blank=True); training=models.TextField(blank=True); eligibility=models.TextField(blank=True); requirements=models.TextField(); posting_date=models.DateField(); deadline=models.DateField(); status=models.CharField(max_length=20,default="OPEN")
    def __str__(self): return self.position
