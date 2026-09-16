from django.conf import settings
from django.db import models
from offices.models import TimeStampedModel
class Ticket(TimeStampedModel):
    number=models.CharField(max_length=40,unique=True); subject=models.CharField(max_length=255); category=models.CharField(max_length=40); description=models.TextField(); priority=models.CharField(max_length=20,default="NORMAL"); status=models.CharField(max_length=30,default="OPEN"); requester=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="tickets"); assigned_to=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name="assigned_tickets")
class TicketReply(TimeStampedModel):
    ticket=models.ForeignKey(Ticket,on_delete=models.CASCADE,related_name="replies"); author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT); message=models.TextField(); internal=models.BooleanField(default=False); attachment=models.FileField(upload_to="tickets/",blank=True)
