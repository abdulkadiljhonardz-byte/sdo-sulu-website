import logging

from django.conf import settings
from django.core.mail import send_mail

from accounts.models import Role, User


logger = logging.getLogger(__name__)


def send_portal_email(subject, message, recipients):
    recipients = sorted({email.strip() for email in recipients if email and email.strip()})
    if not recipients:
        return 0
    try:
        return send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipients,
            fail_silently=False,
        )
    except Exception:
        logger.exception("Portal email delivery failed for subject %s", subject)
        return 0


def administrator_emails():
    configured = [email for _, email in settings.ADMINS]
    database = User.objects.filter(
        role__in=[Role.SUPER_ADMIN, Role.ADMIN], is_active=True
    ).exclude(email="").values_list("email", flat=True)
    return [*configured, *database]


def notify_administrators(subject, message):
    return send_portal_email(subject, message, administrator_emails())
