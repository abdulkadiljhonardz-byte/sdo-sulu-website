from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from core.analytics import record_event
from core.models import AnalyticsEvent

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
