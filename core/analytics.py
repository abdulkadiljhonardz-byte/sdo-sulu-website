from .models import AnalyticsEvent


def record_event(request, event_type, obj=None, query=""):
    """Record privacy-conscious usage analytics without storing IP addresses."""
    AnalyticsEvent.objects.create(
        event_type=event_type,
        path=request.path[:500],
        object_type=obj.__class__.__name__ if obj else "",
        object_id=str(obj.pk) if obj and obj.pk else "",
        query=query[:255],
        user=request.user if request.user.is_authenticated else None,
    )
