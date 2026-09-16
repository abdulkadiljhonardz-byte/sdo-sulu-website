from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from .models import Notification

@login_required
def index(request):
    items=Notification.objects.filter(recipient=request.user)
    return render(request,"notifications/index.html",{"notifications":items})

@login_required
def read(request,pk):
    item=get_object_or_404(Notification,pk=pk,recipient=request.user)
    if request.method=="POST" and not item.read_at:
        item.read_at=timezone.now(); item.save(update_fields=["read_at"])
    return redirect(item.link or "notifications:index")

@login_required
def read_all(request):
    if request.method=="POST": Notification.objects.filter(recipient=request.user,read_at__isnull=True).update(read_at=timezone.now())
    return redirect("notifications:index")
