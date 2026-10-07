from django.db.models import Q
from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.utils import timezone
from core.analytics import record_event
from core.models import AnalyticsEvent
from .models import Issuance
def index(request):
    q=request.GET.get("q","").strip(); category=request.GET.get("category","").strip(); now=timezone.now(); items=Issuance.objects.select_related("office").filter(status="PUBLISHED",archived=False).filter(Q(publish_at__isnull=True)|Q(publish_at__lte=now)).filter(Q(expires_at__isnull=True)|Q(expires_at__gt=now))
    if q:
        record_event(request,AnalyticsEvent.Type.SEARCH,query=q)
        items=items.filter(Q(title__icontains=q)|Q(reference_number__icontains=q)|Q(keywords__icontains=q))
    valid_categories=dict(Issuance.Category.choices)
    if category in valid_categories: items=items.filter(category=category)
    else: category=""
    local_categories = [
        (value, "Division Memorandum" if value == Issuance.Category.DIVISION_MEMO else label)
        for value, label in Issuance.Category.choices
        if not value.startswith("DEPED_")
    ]
    display_labels = dict(local_categories)
    page = Paginator(items, 10).get_page(request.GET.get("page"))
    return render(request,"issuances/list.html",{"items":page,"q":q,"category":category,"category_label":display_labels.get(category,"All Issuances"),"categories":local_categories})


def download(request, pk):
    now = timezone.now()
    item = get_object_or_404(
        Issuance.objects.filter(status="PUBLISHED", archived=False)
        .filter(Q(publish_at__isnull=True) | Q(publish_at__lte=now))
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now)),
        pk=pk,
    )
    if not item.pdf:
        raise Http404("No PDF is available for this issuance.")
    record_event(request, AnalyticsEvent.Type.ISSUANCE_DOWNLOAD, item)
    return FileResponse(item.pdf.open("rb"), as_attachment=True, filename=f"{item.reference_number}.pdf")


def detail(request, pk):
    now = timezone.now()
    item = get_object_or_404(
        Issuance.objects.select_related("office")
        .filter(status="PUBLISHED", archived=False)
        .filter(Q(publish_at__isnull=True) | Q(publish_at__lte=now))
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now)),
        pk=pk,
    )
    return render(request, "issuances/detail.html", {"item": item})
