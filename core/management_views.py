from django.contrib import messages
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Max, Q
from django.db.models.functions import TruncDate
from django.http import FileResponse, HttpResponse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import date, datetime, timedelta

from accounts.models import Role, StaffProfile, User
from audit.models import AuditLog
from audit.utils import record_action
from content.models import Download, News, PublicPage, SiteSetting
from content.facebook_import import FacebookImportError, import_facebook_post
from content.facebook_page_sync import FacebookPageSyncError, sync_facebook_news
from events.models import Event
from feedback.models import Complaint, ContactInquiry, Feedback
from issuances.models import Issuance, IssuanceVersion
from notifications.models import Notification
from notifications.emailing import notify_administrators, send_portal_email
from offices.models import District, Office
from schools.models import School
from vacancies.models import Vacancy
from verification.models import VerifiedDocument
from appointments.models import Appointment
from services.models import ServiceRequest
from tickets.models import Ticket
from .models import AnalyticsEvent

from .management_forms import (
    ComplaintManagementForm,
    ContactInquiryManagementForm,
    DownloadManagementForm,
    EventManagementForm,
    FacebookImportForm,
    IssuanceManagementForm,
    NewsManagementForm,
    NotificationManagementForm,
    OfficeManagementForm,
    DistrictManagementForm,
    PortalSettingsForm,
    PublicPageManagementForm,
    SchoolManagementForm,
    VacancyManagementForm,
    VerifiedDocumentManagementForm,
    BulkImportForm,
    ReportFilterForm,
)
from .data_tools import (
    ImportValidationError,
    import_issuances,
    import_schools,
    report_data,
    write_csv,
    write_pdf,
    write_xlsx,
)


CONTENT_TYPES = {
    "issuances": {"label": "Issuances & Memoranda", "singular": "issuance", "model": Issuance, "form": IssuanceManagementForm, "search": ("title", "reference_number", "keywords"), "office_field": "office", "publish_field": "status", "published_value": "PUBLISHED", "draft_value": "DRAFT"},
    "news": {"label": "News", "singular": "news article", "model": News, "form": NewsManagementForm, "search": ("title", "body", "category"), "office_field": "office", "publish_field": "is_published", "published_value": True, "draft_value": False},
    "downloads": {"label": "Downloads", "singular": "download", "model": Download, "form": DownloadManagementForm, "search": ("title", "category", "description"), "office_field": "office", "publish_field": "published", "published_value": True, "draft_value": False},
    "events": {"label": "Events", "singular": "event", "model": Event, "form": EventManagementForm, "search": ("title", "location", "organizer", "category"), "office_field": "office"},
    "vacancies": {"label": "Job Vacancies", "singular": "vacancy", "model": Vacancy, "form": VacancyManagementForm, "search": ("position", "employment_type", "status"), "office_field": "office"},
    "verified-documents": {"label": "Verified Documents", "singular": "verified document", "model": VerifiedDocument, "form": VerifiedDocumentManagementForm, "search": ("document_number", "recipient", "document_type", "code"), "office_field": "issuing_office"},
    "schools": {"label": "Schools", "singular": "school", "model": School, "form": SchoolManagementForm, "search": ("name", "school_id", "municipality"), "admin_only": True},
    "offices": {"label": "Offices & Sections", "singular": "office", "model": Office, "form": OfficeManagementForm, "search": ("name", "code", "email"), "admin_only": True},
    "districts": {"label": "Districts", "singular": "district", "model": District, "form": DistrictManagementForm, "search": ("name", "municipality"), "admin_only": True},
    "public-pages": {"label": "Public Information Pages", "singular": "public page", "model": PublicPage, "form": PublicPageManagementForm, "search": ("title", "slug", "body"), "admin_only": True},
}


def _config(kind):
    if kind not in CONTENT_TYPES:
        raise PermissionDenied
    return CONTENT_TYPES[kind]


def _can_manage(user, config, action="view"):
    if not user.is_authenticated or not user.is_staff_member:
        return False
    if user.is_superuser or user.role in {Role.SUPER_ADMIN, Role.ADMIN}:
        return True
    if config.get("admin_only"):
        return False
    if config.get("office_field") and not _staff_office(user):
        return False
    model = config["model"]
    return user.has_perm(f"{model._meta.app_label}.{action}_{model._meta.model_name}")


def _staff_office(user):
    try:
        return user.staff_profile.office
    except (AttributeError, StaffProfile.DoesNotExist):
        return None


def _scope_queryset(user, config, queryset):
    if user.is_superuser or user.role in {Role.SUPER_ADMIN, Role.ADMIN}:
        return queryset
    office_field = config.get("office_field")
    if office_field:
        office = _staff_office(user)
        return queryset.filter(**{office_field: office}) if office else queryset.none()
    return queryset


def _prepare_form(user, config, form):
    office_field = config.get("office_field")
    if office_field and office_field in form.fields and user.role == Role.STAFF:
        office = _staff_office(user)
        form.fields[office_field].queryset = Office.objects.filter(pk=getattr(office, "pk", None))
        form.fields[office_field].initial = office
        form.fields[office_field].disabled = True
    publish_field = config.get("publish_field")
    if publish_field in form.fields and user.role == Role.STAFF:
        form.fields[publish_field].disabled = True
        form.initial[publish_field] = config.get("draft_value")
    if "archived" in form.fields and user.role == Role.STAFF:
        form.fields["archived"].disabled = True
        form.initial["archived"] = False


def _is_published(item, config):
    field = config.get("publish_field")
    return bool(field and getattr(item, field) == config.get("published_value"))


def _require(user, config, action="view"):
    if not _can_manage(user, config, action):
        raise PermissionDenied


def _require_system_admin(user):
    if not user.is_authenticated or not (
        user.is_superuser or user.role in {Role.SUPER_ADMIN, Role.ADMIN}
    ):
        raise PermissionDenied


def content_management(request):
    if not request.user.is_authenticated or not request.user.is_staff_member:
        raise PermissionDenied
    cards = []
    for kind, config in CONTENT_TYPES.items():
        if _can_manage(request.user, config):
            queryset = _scope_queryset(request.user, config, config["model"].objects.all())
            cards.append({"kind": kind, "label": config["label"], "count": queryset.count()})
    is_system_admin = request.user.is_superuser or request.user.role in {Role.SUPER_ADMIN, Role.ADMIN}
    return render(request, "management/dashboard.html", {"cards": cards, "is_system_admin": is_system_admin})


def facebook_news_sync(request):
    _require_system_admin(request.user)
    summary = None
    if request.method == "POST":
        try:
            summary = sync_facebook_news(
                start_date=date(2026, 1, 1),
                end_date=date(2027, 12, 31),
                publish=True,
            )
        except FacebookPageSyncError as exc:
            messages.error(request, str(exc))
        else:
            record_action(
                request,
                "Official Facebook News synchronized",
                current=summary.as_dict(),
            )
            messages.success(
                request,
                f"Facebook sync finished: {summary.imported} News imported and "
                f"{summary.excluded_memos} memorandum posts excluded.",
            )
    return render(
        request,
        "management/facebook_sync.html",
        {
            "summary": summary,
            "page_url": settings.FACEBOOK_PAGE_URL,
            "page_id": settings.FACEBOOK_PAGE_ID,
            "token_configured": bool(settings.FACEBOOK_PAGE_ACCESS_TOKEN.strip()),
        },
    )


def portal_settings(request):
    _require_system_admin(request.user)
    keys = {
        "sdo_name": "SDO_NAME",
        "address": "ADDRESS",
        "email": "EMAIL",
        "phone": "PHONE",
        "whatsapp": "WHATSAPP",
        "map_url": "MAP_URL",
        "office_hours": "OFFICE_HOURS",
        "homepage_banner": "HOMEPAGE_BANNER",
        "footer_text": "FOOTER_TEXT",
        "maintenance_mode": "MAINTENANCE_MODE",
    }
    stored = dict(SiteSetting.objects.filter(key__in=keys.values()).values_list("key", "value"))
    initial = {
        "sdo_name": stored.get("SDO_NAME", "Schools Division Office of Sulu"),
        "address": stored.get("ADDRESS", "Scott Road, San Raymundo, Jolo, Sulu"),
        "email": stored.get("EMAIL", "sdskiram.irilis@deped.gov.ph"),
        "phone": stored.get("PHONE", "0965 754 5663"),
        "whatsapp": stored.get("WHATSAPP", "+63 966 175 6976"),
        "map_url": stored.get(
            "MAP_URL",
            "https://www.google.com/maps/place/Department+of+Education/@6.0516351,121.0015126,20z/data=!4m6!3m5!1s0x3244fdcd27283039:0x17e97c0b5fafcf44!8m2!3d6.0516996!4d121.0017765!16s%2Fg%2F1txx_v9q?entry=ttu&g_ep=EgoyMDI2MDkxMy4wIKXMDSoASAFQAw%3D%3D",
        ),
        "office_hours": stored.get("OFFICE_HOURS", "Monday–Friday, 8:00 AM–5:00 PM"),
        "homepage_banner": stored.get("HOMEPAGE_BANNER", ""),
        "footer_text": stored.get("FOOTER_TEXT", "Official Digital Information Portal"),
        "maintenance_mode": stored.get("MAINTENANCE_MODE", "False").lower() == "true",
    }
    form = PortalSettingsForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        for field, key in keys.items():
            value = form.cleaned_data[field]
            if isinstance(value, bool):
                value = str(value)
            SiteSetting.objects.update_or_create(key=key, defaults={"value": value})
        record_action(request, "Portal settings updated", current={"fields": list(keys.values())})
        messages.success(request, "Portal settings were updated.")
        return redirect("core:portal_settings")
    return render(request, "management/settings.html", {"form": form})


def feedback_management(request):
    _require_system_admin(request.user)
    tab = request.GET.get("tab", "inquiries")
    query = request.GET.get("q", "").strip()
    if tab == "inquiries":
        items = ContactInquiry.objects.order_by("-created_at")
        if query:
            items = items.filter(
                Q(name__icontains=query)
                | Q(email__icontains=query)
                | Q(phone__icontains=query)
                | Q(message__icontains=query)
            )
    elif tab == "feedback":
        items = Feedback.objects.order_by("-created_at")
        if query:
            items = items.filter(Q(message__icontains=query) | Q(email__icontains=query))
    else:
        tab = "complaints"
        items = Complaint.objects.order_by("-created_at")
        if query:
            items = items.filter(Q(reference_number__icontains=query) | Q(subject__icontains=query) | Q(details__icontains=query))
    page = Paginator(items, 20).get_page(request.GET.get("page"))
    return render(request, "management/feedback.html", {"page": page, "tab": tab, "query": query})


def contact_inquiry_update(request, pk):
    _require_system_admin(request.user)
    inquiry = get_object_or_404(ContactInquiry, pk=pk)
    previous = {"status": inquiry.status}
    form = ContactInquiryManagementForm(request.POST or None, instance=inquiry)
    if request.method == "POST" and form.is_valid():
        inquiry = form.save()
        record_action(
            request,
            "Contact inquiry status updated",
            inquiry,
            previous=previous,
            current={"status": inquiry.status},
        )
        messages.success(request, "The contact inquiry status was updated.")
        send_portal_email(
            "SDO Sulu inquiry status update",
            f"The status of your inquiry is now {inquiry.get_status_display()}.",
            [inquiry.email],
        )
        return redirect("core:feedback_management")
    return render(
        request,
        "management/contact_inquiry_form.html",
        {"form": form, "inquiry": inquiry},
    )


def complaint_update(request, pk):
    _require_system_admin(request.user)
    complaint = get_object_or_404(Complaint, pk=pk)
    previous = {"status": complaint.status}
    form = ComplaintManagementForm(request.POST or None, instance=complaint)
    if request.method == "POST" and form.is_valid():
        complaint = form.save()
        record_action(request, "Complaint status updated", complaint, previous=previous, current={"status": complaint.status})
        messages.success(request, "Complaint status was updated.")
        send_portal_email(
            f"Complaint {complaint.reference_number} status update",
            f"The status of your complaint is now {complaint.status.replace('_', ' ').title()}.",
            [complaint.email],
        )
        return redirect("core:feedback_management")
    return render(request, "management/complaint_form.html", {"form": form, "complaint": complaint})


def notification_management(request):
    _require_system_admin(request.user)
    form = NotificationManagementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        notification = form.save()
        record_action(request, "Notification sent", notification, current={"recipient": notification.recipient_id, "title": notification.title})
        messages.success(request, "Notification was sent.")
        return redirect("core:notification_management")
    page = Paginator(Notification.objects.select_related("recipient").order_by("-created_at"), 20).get_page(request.GET.get("page"))
    return render(request, "management/notifications.html", {"form": form, "page": page})


def audit_management(request):
    _require_system_admin(request.user)
    query = request.GET.get("q", "").strip()
    logs = AuditLog.objects.select_related("user")
    if query:
        logs = logs.filter(Q(action__icontains=query) | Q(object_type__icontains=query) | Q(user__username__icontains=query))
    page = Paginator(logs, 30).get_page(request.GET.get("page"))
    return render(request, "management/audit.html", {"page": page, "query": query})


def legacy_records(request):
    _require_system_admin(request.user)
    context = {
        "request_count": ServiceRequest.objects.count(),
        "appointment_count": Appointment.objects.count(),
        "ticket_count": Ticket.objects.count(),
        "requests": ServiceRequest.objects.select_related("service", "requester").order_by("-created_at")[:10],
        "appointments": Appointment.objects.select_related("office", "user").order_by("-created_at")[:10],
        "tickets": Ticket.objects.select_related("requester").order_by("-created_at")[:10],
    }
    return render(request, "management/legacy.html", context)


def analytics_dashboard(request):
    _require_system_admin(request.user)
    since = timezone.now() - timedelta(days=30)
    recent = AnalyticsEvent.objects.filter(created_at__gte=since)
    usage = {row["event_type"]: row["total"] for row in recent.values("event_type").annotate(total=Count("id"))}
    daily_rows = recent.annotate(day=TruncDate("created_at")).values("day").annotate(total=Count("id")).order_by("day")
    max_daily = max((row["total"] for row in daily_rows), default=1)
    top_searches = recent.filter(event_type=AnalyticsEvent.Type.SEARCH).exclude(query="").values("query").annotate(total=Count("id")).order_by("-total")[:10]
    top_news_events = recent.filter(event_type=AnalyticsEvent.Type.NEWS_VIEW).exclude(object_id="").values("object_id").annotate(total=Count("id")).order_by("-total")[:10]
    news_map = {str(item.pk): item.title for item in News.objects.filter(pk__in=[row["object_id"] for row in top_news_events])}
    top_news = [{"title": news_map.get(row["object_id"], "Deleted news item"), "total": row["total"]} for row in top_news_events]
    context = {
        "published_issuances": Issuance.objects.filter(status="PUBLISHED", archived=False).filter(Q(publish_at__isnull=True)|Q(publish_at__lte=timezone.now())).filter(Q(expires_at__isnull=True)|Q(expires_at__gt=timezone.now())).count(),
        "published_news": News.objects.filter(is_published=True, archived=False).filter(Q(published_at__isnull=True)|Q(published_at__lte=timezone.now())).filter(Q(expires_at__isnull=True)|Q(expires_at__gt=timezone.now())).count(),
        "download_count": usage.get(AnalyticsEvent.Type.ISSUANCE_DOWNLOAD, 0) + usage.get(AnalyticsEvent.Type.RESOURCE_DOWNLOAD, 0),
        "search_count": usage.get(AnalyticsEvent.Type.SEARCH, 0),
        "directory_usage": usage.get(AnalyticsEvent.Type.DIRECTORY_VISIT, 0) + usage.get(AnalyticsEvent.Type.SCHOOL_VIEW, 0),
        "open_complaints": Complaint.objects.exclude(status="CLOSED").count(),
        "active_staff": User.objects.filter(is_active=True, role__in=[Role.SUPER_ADMIN, Role.ADMIN, Role.STAFF]).count(),
        "daily_usage": [{"day": row["day"], "total": row["total"], "percent": round(row["total"] * 100 / max_daily)} for row in daily_rows],
        "top_searches": top_searches,
        "top_news": top_news,
    }
    return render(request, "management/analytics.html", context)


def data_workspace(request):
    _require_system_admin(request.user)
    form = BulkImportForm(request.POST or None, request.FILES or None)
    import_errors = []
    if request.method == "POST" and form.is_valid():
        try:
            if form.cleaned_data["dataset"] == "schools":
                imported = import_schools(form.cleaned_data["spreadsheet"])
            else:
                imported = import_issuances(
                    form.cleaned_data["spreadsheet"],
                    form.cleaned_data["pdf_files"],
                    request.user,
                )
        except ImportValidationError as exc:
            import_errors = exc.errors
        else:
            record_action(request, "Bulk data imported", current={"dataset": form.cleaned_data["dataset"], "rows": imported})
            messages.success(request, f"Successfully imported {imported} {form.cleaned_data['dataset']} records.")
            return redirect("core:data_workspace")
    return render(request, "management/data_workspace.html", {"form": form, "import_errors": import_errors})


def import_template(request, dataset, file_format):
    _require_system_admin(request.user)
    templates = {
        "schools": ["school_id", "name", "district", "classification", "municipality", "school_type", "level", "school_head", "address", "barangay", "contact_number", "email", "latitude", "longitude", "status", "student_population", "teacher_population"],
        "issuances": ["reference_number", "title", "category", "year", "date_issued", "office_code", "keywords", "pdf_filename"],
    }
    if dataset not in templates or file_format not in {"csv", "xlsx"}:
        raise PermissionDenied
    if file_format == "xlsx":
        payload = write_xlsx(templates[dataset], [])
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        payload = write_csv(templates[dataset], [])
        content_type = "text/csv; charset=utf-8"
    response = HttpResponse(payload, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{dataset}-import-template.{file_format}"'
    return response


def export_data(request, report, file_format):
    _require_system_admin(request.user)
    if report not in dict(ReportFilterForm.REPORT_CHOICES) or file_format not in {"csv", "xlsx", "pdf"}:
        raise PermissionDenied
    date_from = request.GET.get("date_from") or None
    date_to = request.GET.get("date_to") or None
    try:
        date_from = datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else None
        date_to = datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else None
    except ValueError:
        raise PermissionDenied
    if date_from and date_to and date_to < date_from:
        raise PermissionDenied
    headers, rows = report_data(report, date_from, date_to)
    if file_format == "xlsx":
        payload, content_type = write_xlsx(headers, rows), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif file_format == "pdf":
        payload, content_type = write_pdf(f"SDO Sulu — {dict(ReportFilterForm.REPORT_CHOICES)[report]}", headers, rows), "application/pdf"
    else:
        payload, content_type = write_csv(headers, rows), "text/csv; charset=utf-8"
    response = HttpResponse(payload, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="sdo-sulu-{report}.{file_format}"'
    record_action(request, "Report exported", current={"report": report, "format": file_format, "rows": len(rows)})
    return response


def reports(request):
    _require_system_admin(request.user)
    form = ReportFilterForm(request.GET or None)
    headers, rows, selected = [], [], ""
    if form.is_valid():
        selected = form.cleaned_data["report"]
        headers, rows = report_data(selected, form.cleaned_data.get("date_from"), form.cleaned_data.get("date_to"))
    return render(request, "management/reports.html", {"form": form, "headers": headers, "rows": rows[:100], "total": len(rows), "selected": selected})


def content_list(request, kind):
    config = _config(kind)
    _require(request.user, config)
    query = request.GET.get("q", "").strip()
    items = _scope_queryset(
        request.user, config, config["model"].objects.all()
    ).order_by("-updated_at")
    if query:
        search_query = Q()
        for field in config["search"]:
            search_query |= Q(**{f"{field}__icontains": query})
        items = items.filter(search_query)
    page = Paginator(items, 20).get_page(request.GET.get("page"))
    can_delete = kind in {"news", "issuances"} and (
        request.user.is_superuser
        or request.user.role in {Role.SUPER_ADMIN, Role.ADMIN}
    )
    return render(request, "management/list.html", {"config": config, "kind": kind, "page": page, "query": query, "can_add": _can_manage(request.user, config, "add"), "can_change": _can_manage(request.user, config, "change"), "can_delete": can_delete})


def content_create(request, kind):
    config = _config(kind)
    _require(request.user, config, "add")
    form = config["form"](request.POST or None, request.FILES or None)
    _prepare_form(request.user, config, form)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        office_field = config.get("office_field")
        if office_field and request.user.role == Role.STAFF:
            setattr(item, office_field, _staff_office(request.user))
        if hasattr(item, "author_id"):
            item.author = request.user
        if hasattr(item, "created_by_id"):
            item.created_by = request.user
        if request.user.role == Role.STAFF and config.get("publish_field"):
            setattr(item, config["publish_field"], config["draft_value"])
        item.save()
        form.save_m2m()
        record_action(request, f"{config['singular'].title()} created", item, current={"label": str(item), "kind": kind})
        messages.success(request, f"The {config['singular']} was added successfully.")
        if request.user.role == Role.STAFF:
            notify_administrators(
                f"Content submitted for review: {config['label']}",
                f"{request.user.get_full_name() or request.user.username} submitted {item} from {_staff_office(request.user)}. Review it in the SDO Sulu System Administration portal.",
            )
        return redirect("core:content_list", kind=kind)
    return render(request, "management/form.html", {
        "form": form,
        "config": config,
        "kind": kind,
        "heading": f"Add {config['singular']}",
        "facebook_import_form": FacebookImportForm() if kind == "news" else None,
        "can_publish_import": request.user.is_superuser or request.user.role in {Role.SUPER_ADMIN, Role.ADMIN},
    })


@require_POST
def facebook_import(request, kind):
    config = _config(kind)
    if kind != "news":
        raise PermissionDenied
    _require(request.user, config, "add")
    import_form = FacebookImportForm(request.POST)
    if not import_form.is_valid():
        messages.error(request, "Enter a valid public Facebook post link.")
        return redirect("core:content_create", kind=kind)

    source_url = import_form.cleaned_data["facebook_url"]
    existing = _scope_queryset(
        request.user,
        config,
        config["model"].objects.filter(source_url=source_url),
    ).first()
    if existing:
        messages.info(request, "That Facebook post has already been imported.")
        if _can_manage(request.user, config, "change"):
            return redirect("core:content_update", kind=kind, pk=existing.pk)
        return redirect("core:content_list", kind=kind)

    try:
        imported = import_facebook_post(source_url)
    except FacebookImportError as exc:
        messages.error(request, str(exc))
        return redirect("core:content_create", kind=kind)

    upload = SimpleUploadedFile(
        imported.image_name,
        imported.image_bytes,
        content_type=imported.image_content_type,
    )
    data = {
        "title": imported.title,
        "body": imported.caption,
        "category": "Facebook Update",
        "source_url": imported.url,
    }
    if request.user.role == Role.STAFF:
        office = _staff_office(request.user)
        if office:
            data["office"] = office.pk
    form = config["form"](data, {"cover_image": upload})
    _prepare_form(request.user, config, form)
    if not form.is_valid():
        messages.error(
            request,
            "Facebook returned incomplete content. Upload the photo and caption manually.",
        )
        return redirect("core:content_create", kind=kind)

    item = form.save(commit=False)
    if request.user.role == Role.STAFF:
        item.office = _staff_office(request.user)
    item.author = request.user
    can_publish = request.user.is_superuser or request.user.role in {
        Role.SUPER_ADMIN,
        Role.ADMIN,
    }
    item.is_published = bool(
        can_publish and import_form.cleaned_data.get("publish_now")
    )
    if item.is_published:
        item.published_at = timezone.now()
    item.source_imported_at = timezone.now()
    item.save()
    record_action(
        request,
        f"{config['singular'].title()} imported from Facebook",
        item,
        current={
            "kind": kind,
            "source_url": imported.url,
            "status": "published" if item.is_published else "draft",
        },
    )
    if item.is_published:
        messages.success(
            request,
            "Facebook caption and photo were imported and published. You can still review or edit the news item.",
        )
    else:
        messages.success(
            request,
            "Facebook caption and photo were imported as a draft for administrator review.",
        )
    return redirect("core:content_update", kind=kind, pk=item.pk)


@transaction.atomic
def content_update(request, kind, pk):
    config = _config(kind)
    _require(request.user, config, "change")
    queryset = config["model"].objects.all()
    if kind == "issuances":
        queryset = queryset.select_for_update()
    item = get_object_or_404(_scope_queryset(request.user, config, queryset), pk=pk)
    original_pdf_name = item.pdf.name if kind == "issuances" and item.pdf else ""
    was_published = _is_published(item, config)
    if request.user.role == Role.STAFF and was_published:
        raise PermissionDenied
    previous = {"label": str(item), "published": was_published}
    form = config["form"](request.POST or None, request.FILES or None, instance=item)
    _prepare_form(request.user, config, form)
    if request.method == "POST" and form.is_valid():
        if kind == "issuances" and request.FILES.get("pdf") and original_pdf_name:
            next_version = (item.versions.aggregate(Max("version_number"))["version_number__max"] or 0) + 1
            IssuanceVersion.objects.create(
                issuance=item,
                version_number=next_version,
                file=original_pdf_name,
                reason=form.cleaned_data["revision_reason"],
                uploaded_by=request.user,
            )
        item = form.save(commit=False)
        office_field = config.get("office_field")
        if office_field and request.user.role == Role.STAFF:
            setattr(item, office_field, _staff_office(request.user))
        if request.user.role == Role.STAFF and config.get("publish_field"):
            setattr(item, config["publish_field"], config["draft_value"])
        item.save()
        form.save_m2m()
        record_action(request, f"{config['singular'].title()} updated", item, previous=previous, current={"label": str(item), "kind": kind})
        messages.success(request, f"The {config['singular']} was updated successfully.")
        if request.user.role == Role.STAFF:
            notify_administrators(
                f"Content update submitted for review: {config['label']}",
                f"{request.user.get_full_name() or request.user.username} updated {item}. Review it in the SDO Sulu System Administration portal.",
            )
        elif not was_published and _is_published(item, config):
            owner = getattr(item, "author", None) or getattr(item, "created_by", None)
            if owner:
                send_portal_email(
                    f"Your {config['singular']} was published",
                    f"{item} has been reviewed and published on the SDO Sulu portal.",
                    [owner.email],
                )
        return redirect("core:content_list", kind=kind)
    versions = item.versions.select_related("uploaded_by") if kind == "issuances" else None
    return render(request, "management/form.html", {
        "form": form,
        "config": config,
        "kind": kind,
        "heading": f"Edit {config['singular']}",
        "item": item,
        "versions": versions,
        "facebook_import_form": None,
    })


def issuance_version_download(request, pk):
    config = CONTENT_TYPES["issuances"]
    _require(request.user, config)
    version = get_object_or_404(
        IssuanceVersion.objects.select_related("issuance"), pk=pk
    )
    scoped = _scope_queryset(request.user, config, Issuance.objects.filter(pk=version.issuance_id))
    if not scoped.exists():
        raise PermissionDenied
    return FileResponse(version.file.open("rb"), as_attachment=True, filename=f"{version.issuance.reference_number}-v{version.version_number}.pdf")


def content_preview(request, kind, pk):
    config = _config(kind)
    _require(request.user, config)
    item = get_object_or_404(
        _scope_queryset(request.user, config, config["model"].objects.all()), pk=pk
    )
    return render(request, "management/preview.html", {"item": item, "kind": kind, "config": config, "can_change": _can_manage(request.user, config, "change")})


def content_archive(request, kind, pk):
    config = _config(kind)
    _require(request.user, config, "change")
    if request.method != "POST" or request.POST.get("confirm") != "ARCHIVE":
        raise PermissionDenied
    item = get_object_or_404(
        _scope_queryset(request.user, config, config["model"].objects.all()), pk=pk
    )
    if request.user.role == Role.STAFF and _is_published(item, config):
        raise PermissionDenied
    if hasattr(item, "archived"):
        item.archived = True
    if hasattr(item, "is_published"):
        item.is_published = False
    if hasattr(item, "published"):
        item.published = False
    if kind == "issuances":
        item.status = "ARCHIVED"
    fields = [name for name in ("archived", "is_published", "published", "status") if hasattr(item, name)]
    item.save(update_fields=[*fields, "updated_at"])
    record_action(request, f"{config['singular'].title()} archived", item, current={"kind": kind})
    messages.success(request, f"The {config['singular']} was archived.")
    return redirect("core:content_list", kind=kind)


@transaction.atomic
def content_delete(request, kind, pk):
    """Permanently delete News or an Issuance after an explicit admin POST."""
    if kind not in {"news", "issuances"}:
        raise PermissionDenied
    _require_system_admin(request.user)
    if request.method != "POST" or request.POST.get("confirm") != "DELETE":
        raise PermissionDenied

    config = _config(kind)
    item = get_object_or_404(config["model"].objects.select_for_update(), pk=pk)
    item_id = item.pk
    label = str(item)
    stored_files = []
    stored_keys = set()

    def remember(field_file):
        key = (id(field_file.storage), field_file.name) if field_file else None
        if field_file and field_file.name and key not in stored_keys:
            stored_keys.add(key)
            stored_files.append((field_file.storage, field_file.name))

    remember(getattr(item, "cover_image", None))
    remember(getattr(item, "pdf", None))
    if kind == "issuances":
        for version in item.versions.all():
            remember(version.file)

    record_action(
        request,
        f"{config['singular'].title()} permanently deleted",
        item,
        previous={"id": item_id, "label": label, "kind": kind},
        current={"deleted": True},
    )
    item.delete()

    for storage, name in stored_files:
        transaction.on_commit(
            lambda storage=storage, name=name: storage.delete(name),
            robust=True,
        )
    messages.success(request, f'The {config["singular"]} “{label}” was permanently deleted.')
    return redirect("core:content_list", kind=kind)
