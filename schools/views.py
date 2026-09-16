from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from core.analytics import record_event
from core.models import AnalyticsEvent
from .models import School
def directory(request):
    record_event(request,AnalyticsEvent.Type.DIRECTORY_VISIT)
    schools=School.objects.select_related("district").all(); q=request.GET.get("q",""); district=request.GET.get("district","")
    if q: schools=schools.filter(Q(name__icontains=q)|Q(school_id__icontains=q))
    if district: schools=schools.filter(district_id=district)
    return render(request,"schools/directory.html",{"schools":schools,"districts":__import__("offices.models",fromlist=["District"]).District.objects.all()})
def detail(request,pk):
    school=get_object_or_404(School,pk=pk)
    record_event(request,AnalyticsEvent.Type.SCHOOL_VIEW,school)
    return render(request,"schools/detail.html",{"school":school})
