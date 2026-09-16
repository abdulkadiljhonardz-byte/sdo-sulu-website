from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, render
from core.analytics import record_event
from core.models import AnalyticsEvent
from offices.models import District
from .models import School


def directory(request):
    record_event(request, AnalyticsEvent.Type.DIRECTORY_VISIT)
    query = request.GET.get("q", "").strip()
    selected_district = request.GET.get("district", "").strip()
    schools = School.objects.select_related("district").filter(status="ACTIVE")
    if query:
        schools = schools.filter(
            Q(name__icontains=query)
            | Q(school_id__icontains=query)
            | Q(municipality__icontains=query)
            | Q(barangay__icontains=query)
        )
    if selected_district.isdigit():
        schools = schools.filter(district_id=selected_district)

    districts = (
        District.objects.filter(active=True)
        .annotate(
            listed_public_schools=Count(
                "schools",
                filter=Q(schools__classification="PUBLIC", schools__status="ACTIVE"),
            )
        )
        .order_by("name")
    )
    total_target = districts.aggregate(target=Sum("public_school_target"))["target"] or 0
    listed_public_schools = School.objects.filter(
        district__active=True,
        classification="PUBLIC",
        status="ACTIVE",
    ).count()
    page = Paginator(schools.order_by("name"), 20).get_page(request.GET.get("page"))
    return render(
        request,
        "schools/directory.html",
        {
            "schools": page,
            "page": page,
            "districts": districts,
            "district_count": districts.count(),
            "total_target": total_target,
            "listed_public_schools": listed_public_schools,
            "query": query,
            "selected_district": selected_district,
        },
    )


def detail(request,pk):
    school=get_object_or_404(School,pk=pk)
    record_event(request,AnalyticsEvent.Type.SCHOOL_VIEW,school)
    return render(request,"schools/detail.html",{"school":school})
