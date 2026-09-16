from .models import AuditLog
from core.validators import client_ip


def record_action(request, action, obj=None, previous=None, current=None):
    AuditLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action=action,
        object_type=obj.__class__.__name__ if obj else "System",
        object_id=str(obj.pk) if obj and obj.pk else "",
        previous_value=previous,
        new_value=current,
        ip_address=client_ip(request),
    )
