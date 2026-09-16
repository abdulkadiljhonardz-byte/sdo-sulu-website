from django.conf import settings
from django.db import models
class AuditLog(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL); action=models.CharField(max_length=200); object_type=models.CharField(max_length=100); object_id=models.CharField(max_length=64,blank=True); previous_value=models.JSONField(null=True,blank=True); new_value=models.JSONField(null=True,blank=True); ip_address=models.GenericIPAddressField(null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=["-created_at"]
