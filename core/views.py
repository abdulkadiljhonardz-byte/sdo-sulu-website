from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from content.models import Download, News
from events.models import Event
from schools.models import School
from issuances.models import Issuance
from vacancies.models import Vacancy
from .analytics import record_event
from .models import AnalyticsEvent


def _active_window(queryset, publish_field, expiry_field="expires_at"):
    now = timezone.now()
    return queryset.filter(
        Q(**{f"{publish_field}__isnull": True}) | Q(**{f"{publish_field}__lte": now})
    ).filter(Q(**{f"{expiry_field}__isnull": True}) | Q(**{f"{expiry_field}__gt": now}))

def home(request):
    from django.utils import timezone

    return render(request, "core/home.html", {
        "news": _active_window(News.objects.filter(is_published=True, archived=False), "published_at")[:3],
        "events": Event.objects.filter(start__gte=timezone.now()).order_by("start")[:4],
        "latest_memos": _active_window(
            Issuance.objects.filter(
                status="PUBLISHED",
                archived=False,
                category__in=[
                    Issuance.Category.DIVISION_MEMO,
                    Issuance.Category.OFFICE_MEMO,
                    Issuance.Category.UNNUMBERED_MEMO,
                    Issuance.Category.DEPED_MEMORANDUM,
                ],
            ),
            "publish_at",
        ).select_related("office")[:4],
        "downloads": _active_window(Download.objects.filter(published=True, archived=False), "publish_at").order_by("-created_at")[:4],
        "open_vacancies": Vacancy.objects.filter(status="OPEN").select_related("office").order_by("deadline")[:3],
        "stats": {
            "schools": School.objects.count(),
            "issuances": Issuance.objects.filter(status="PUBLISHED").count(),
            "vacancies": Vacancy.objects.filter(status="OPEN").count(),
        },
    })
def search(request):
    q = request.GET.get("q", "").strip()
    if q:
        record_event(request, AnalyticsEvent.Type.SEARCH, query=q)
        news = _active_window(
            News.objects.filter(is_published=True, archived=False), "published_at"
        ).filter(Q(title__icontains=q) | Q(body__icontains=q))[:10]
        issuances = _active_window(
            Issuance.objects.filter(status="PUBLISHED", archived=False), "publish_at"
        ).filter(Q(title__icontains=q) | Q(reference_number__icontains=q))[:10]
        schools = School.objects.filter(name__icontains=q)[:10]
    else:
        news, schools, issuances = [], [], []
    return render(
        request,
        "core/search.html",
        {
            "q": q,
            "news": news,
            "schools": schools,
            "issuances": issuances,
        },
    )
@login_required
def dashboard(request):
    from notifications.models import Notification
    ctx={"notifications":Notification.objects.filter(recipient=request.user)[:5],"unread_notifications":Notification.objects.filter(recipient=request.user,read_at__isnull=True).count()}
    return render(request,"dashboards/dashboard.html",ctx)
def error_400(request,exception=None): return render(request,"errors/400.html",status=400)
def error_403(request,exception=None): return render(request,"errors/403.html",status=403)
def error_404(request,exception=None): return render(request,"errors/404.html",status=404)
def error_500(request): return render(request,"errors/500.html",status=500)


def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return JsonResponse({"status": "ok", "database": "ok"})
