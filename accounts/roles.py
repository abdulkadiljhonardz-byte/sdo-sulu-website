from django.contrib.auth.models import Permission

from .models import Role


STAFF_CONTENT_APPS = {
    "content",
    "events",
    "issuances",
    "offices",
    "schools",
    "vacancies",
    "verification",
}


def synchronize_role_permissions(user):
    """Apply conservative Django admin permissions for a portal role."""
    user.is_staff = user.role in {Role.SUPER_ADMIN, Role.ADMIN, Role.STAFF}
    user.user_permissions.clear()

    if user.role == Role.ADMIN:
        permissions = Permission.objects.exclude(
            content_type__app_label__in={
                "accounts", "admin", "audit", "auth", "contenttypes", "sessions"
            }
        )
        user.user_permissions.set(permissions)
    elif user.role == Role.STAFF:
        permissions = Permission.objects.filter(
            content_type__app_label__in=STAFF_CONTENT_APPS,
            codename__in=[
                "add_news", "change_news", "view_news",
                "add_announcement", "change_announcement", "view_announcement",
                "add_download", "change_download", "view_download",
                "add_event", "change_event", "view_event",
                "add_issuance", "change_issuance", "view_issuance",
                "view_office", "add_school", "view_school", "change_school",
                "add_vacancy", "change_vacancy", "view_vacancy",
                "add_verifieddocument", "change_verifieddocument", "view_verifieddocument",
            ],
        )
        user.user_permissions.set(permissions)

    user.save(update_fields=["is_staff"])
