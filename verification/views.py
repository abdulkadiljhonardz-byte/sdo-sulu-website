from django.shortcuts import render
from .models import VerifiedDocument
def check(request):
    code=request.GET.get("code",""); document=VerifiedDocument.objects.select_related("issuing_office").filter(code=code).first() if code else None
    return render(request,"verification/check.html",{"document":document,"code":code})
