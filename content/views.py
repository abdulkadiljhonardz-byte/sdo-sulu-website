import hashlib

from django.contrib import messages
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.analytics import record_event
from core.models import AnalyticsEvent
from core.validators import client_ip
from audit.utils import record_action
from feedback.forms import ContactInquiryForm
from notifications.emailing import notify_administrators, send_portal_email

from .models import Announcement, Download, News, PublicPage


def _published(model):
    now = timezone.now()
    return model.objects.filter(is_published=True, archived=False).filter(
        Q(published_at__isnull=True) | Q(published_at__lte=now)
    ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))


def _publication_list(request, model, template):
    query = request.GET.get("q", "").strip()
    items = _published(model).select_related("office", "author")
    if query:
        items = items.filter(
            Q(title__icontains=query)
            | Q(body__icontains=query)
            | Q(category__icontains=query)
        )
    page = Paginator(items, 9).get_page(request.GET.get("page"))
    return render(request, template, {"page": page, "items": page, "query": query})


def news_list(request):
    return _publication_list(request, News, "content/news_list.html")


def news_detail(request, slug):
    item = get_object_or_404(
        _published(News).select_related("office", "author"), slug=slug
    )
    record_event(request, AnalyticsEvent.Type.NEWS_VIEW, item)
    return render(request, "content/news_detail.html", {"item": item})


def announcement_list(request):
    return _publication_list(request, Announcement, "content/announcement_list.html")


def announcement_detail(request, slug):
    item = get_object_or_404(
        _published(Announcement).select_related("office", "author"), slug=slug
    )
    return render(request, "content/announcement_detail.html", {"item": item})


def public_page(request, slug):
    return render(
        request,
        "content/public_page.html",
        {"page": get_object_or_404(PublicPage, slug=slug, published=True)},
    )


def mission_vision(request):
    pages = PublicPage.objects.filter(
        slug__in=("mission", "vision"), published=True
    ).in_bulk(field_name="slug")
    mission = pages.get("mission")
    vision = pages.get("vision")
    if not mission or not vision:
        # Keep unpublished system pages private and return the standard 404 page.
        get_object_or_404(PublicPage, slug="mission", published=True)
        get_object_or_404(PublicPage, slug="vision", published=True)
    return render(
        request,
        "content/mission_vision.html",
        {"mission": mission, "vision": vision},
    )


def contact_page(request):
    page = get_object_or_404(PublicPage, slug="contact", published=True)
    initial = {}
    if request.user.is_authenticated:
        initial = {
            "name": request.user.get_full_name(),
            "email": request.user.email,
            "phone": getattr(request.user, "phone", ""),
        }
    form = ContactInquiryForm(request.POST or None, initial=initial)
    remote_ip = client_ip(request) or "unknown"
    identity = hashlib.sha256(remote_ip.encode()).hexdigest()
    rate_key = f"contact-inquiry:{identity}"
    if request.method == "POST" and cache.get(rate_key, 0) >= 5:
        return render(request, "errors/429.html", status=429)
    if request.method == "POST" and form.is_valid():
        inquiry = form.save(commit=False)
        inquiry.ip_address = None if remote_ip == "unknown" else remote_ip
        inquiry.save()
        cache.set(rate_key, cache.get(rate_key, 0) + 1, 60 * 60)
        record_action(
            request,
            "Contact inquiry submitted",
            inquiry,
            current={"email": inquiry.email, "status": inquiry.status},
        )
        notify_administrators(
            "New SDO Sulu contact inquiry",
            f"{inquiry.name} submitted a public inquiry. Review it in System Administration.",
        )
        send_portal_email(
            "SDO Sulu inquiry received",
            "We received your message. An authorized SDO Sulu staff member will review it.",
            [inquiry.email],
        )
        messages.success(request, "Your inquiry was sent successfully. Thank you for contacting SDO Sulu.")
        return redirect("pages:contact")
    return render(request, "content/contact.html", {"page": page, "form": form})


def download_resource(request, pk):
    now = timezone.now()
    item = get_object_or_404(
        Download.objects.filter(published=True, archived=False)
        .filter(Q(publish_at__isnull=True) | Q(publish_at__lte=now))
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now)),
        pk=pk,
    )
    record_event(request, AnalyticsEvent.Type.RESOURCE_DOWNLOAD, item)
    return FileResponse(
        item.file.open("rb"),
        as_attachment=True,
        filename=item.file.name.rsplit("/", 1)[-1],
    )
