from django.db.models import Q
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

    districts = District.objects.filter(active=True).order_by("name")
    schools = schools.order_by("district__name", "name")
    return render(
        request,
        "schools/directory.html",
        {
            "schools": schools,
            "result_count": schools.count(),
            "districts": districts,
            "district_count": districts.count(),
            "query": query,
            "selected_district": selected_district,
        },
    )


def detail(request,pk):
    school=get_object_or_404(School,pk=pk)
    record_event(request,AnalyticsEvent.Type.SCHOOL_VIEW,school)
    return render(request,"schools/detail.html",{"school":school})
