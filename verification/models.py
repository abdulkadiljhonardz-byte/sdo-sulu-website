import uuid
from django.db import models
from offices.models import Office, TimeStampedModel
class VerifiedDocument(TimeStampedModel):
    code=models.CharField(max_length=64,unique=True,default=uuid.uuid4,editable=False); document_number=models.CharField(max_length=120,unique=True); recipient=models.CharField(max_length=255); document_type=models.CharField(max_length=100); issuing_office=models.ForeignKey(Office,on_delete=models.PROTECT); date_issued=models.DateField(); status=models.CharField(max_length=20,default="VALID",choices=[(x,x) for x in ["VALID","INVALID","REVOKED","EXPIRED"]])
