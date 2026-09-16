import uuid
from django.conf import settings
from django.db import models
from offices.models import Office, TimeStampedModel

def private_upload(instance, filename): return f"requests/{uuid.uuid4().hex}"
class Service(TimeStampedModel):
    name = models.CharField(max_length=200); office = models.ForeignKey(Office, on_delete=models.PROTECT)
    description = models.TextField(blank=True); active = models.BooleanField(default=True)
    def __str__(self): return self.name
class ServiceRequirement(TimeStampedModel):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="requirements")
    name = models.CharField(max_length=200); required = models.BooleanField(default=True)
class ServiceRequest(TimeStampedModel):
    class Status(models.TextChoices):
        SUBMITTED="SUBMITTED","Submitted"; REVIEW="REVIEW","Under Review"; PROCESSING="PROCESSING","Processing"; APPROVAL="APPROVAL","For Approval"; APPROVED="APPROVED","Approved"; READY="READY","Ready for Release"; RELEASED="RELEASED","Released"; REJECTED="REJECTED","Rejected"; CANCELLED="CANCELLED","Cancelled"; CORRECTION="CORRECTION","Returned for Correction"
    tracking_number=models.CharField(max_length=40, unique=True, editable=False)
    service=models.ForeignKey(Service,on_delete=models.PROTECT); requester=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="service_requests")
    assigned_to=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name="assigned_requests")
    purpose=models.TextField(); status=models.CharField(max_length=20,choices=Status.choices,default=Status.SUBMITTED); staff_remarks=models.TextField(blank=True); result_file=models.FileField(upload_to=private_upload,blank=True)
    def save(self,*args,**kwargs):
        if not self.tracking_number:
            from django.utils.timezone import now
            self.tracking_number=f"SDOSULU-{now():%Y}-{ServiceRequest.objects.filter(created_at__year=now().year).count()+1:06d}"
        return super().save(*args,**kwargs)
class RequestAttachment(TimeStampedModel):
    request=models.ForeignKey(ServiceRequest,on_delete=models.CASCADE,related_name="attachments"); requirement=models.ForeignKey(ServiceRequirement,null=True,blank=True,on_delete=models.SET_NULL); file=models.FileField(upload_to=private_upload)
class RequestHistory(TimeStampedModel):
    request=models.ForeignKey(ServiceRequest,on_delete=models.CASCADE,related_name="history"); status=models.CharField(max_length=20); remarks=models.TextField(blank=True); actor=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL)
