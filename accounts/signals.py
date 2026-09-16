from django.contrib.auth.signals import user_logged_in,user_logged_out,user_login_failed
from django.dispatch import receiver
from audit.models import AuditLog
from core.validators import client_ip

@receiver(user_logged_in)
def login_audit(sender,request,user,**kwargs):
    AuditLog.objects.create(user=user,action="User login",object_type="User",object_id=str(user.pk),ip_address=client_ip(request))

@receiver(user_logged_out)
def logout_audit(sender,request,user,**kwargs):
    if user: AuditLog.objects.create(user=user,action="User logout",object_type="User",object_id=str(user.pk),ip_address=client_ip(request))

@receiver(user_login_failed)
def failed_login_audit(sender,credentials,request,**kwargs):
    AuditLog.objects.create(action="Failed login",object_type="User",new_value={"identifier":credentials.get("username","")[:150]},ip_address=client_ip(request) if request else None)
