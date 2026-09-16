from django.shortcuts import render
from .models import Event
def index(request): return render(request,"events/list.html",{"items":Event.objects.order_by("start")})
