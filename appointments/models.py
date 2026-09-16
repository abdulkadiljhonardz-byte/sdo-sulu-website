from django.conf import settings
from django.db import models
from offices.models import Office, TimeStampedModel
class AppointmentSchedule(TimeStampedModel):
    office=models.ForeignKey(Office,on_delete=models.CASCADE); weekday=models.PositiveSmallIntegerField(); start_time=models.TimeField(); end_time=models.TimeField(); capacity=models.PositiveIntegerField(default=1); active=models.BooleanField(default=True)
class Appointment(TimeStampedModel):
    status=models.CharField(max_length=20,default="PENDING",choices=[(x,x.title()) for x in ["PENDING","APPROVED","REJECTED","COMPLETED","NO_SHOW","CANCELLED"]])
    reference_number=models.CharField(max_length=40,unique=True); user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT); office=models.ForeignKey(Office,on_delete=models.PROTECT); service=models.ForeignKey("services.Service",null=True,blank=True,on_delete=models.SET_NULL); date=models.DateField(); slot=models.ForeignKey(AppointmentSchedule,on_delete=models.PROTECT); purpose=models.TextField()
    class Meta: constraints=[models.UniqueConstraint(fields=["slot","date","user"],name="unique_user_appointment")]
