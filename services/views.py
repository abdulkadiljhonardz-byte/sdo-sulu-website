from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import get_object_or_404,redirect,render
from audit.utils import record_action
from notifications.models import Notification
from .forms import ServiceRequestForm,StatusForm
from .models import RequestAttachment,RequestHistory, ServiceRequest
@login_required
def submit(request):
    form=ServiceRequestForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        item=form.save(commit=False); item.requester=request.user; item.save()
        for upload in form.cleaned_data.get("attachments",[]): RequestAttachment.objects.create(request=item,file=upload)
        RequestHistory.objects.create(request=item,status=item.status,actor=request.user); record_action(request,"Service request submitted",item,current={"tracking":item.tracking_number}); return redirect("services:detail",item.tracking_number)
    return render(request,"services/submit.html",{"form":form})
@login_required
def detail(request,tracking):
    item=get_object_or_404(ServiceRequest,tracking_number=tracking)
    if item.requester_id!=request.user.id and not request.user.is_staff_member: raise PermissionDenied
    return render(request,"services/detail.html",{"item":item})
@login_required
def update(request,tracking):
    if not request.user.is_staff_member: raise PermissionDenied
    item=get_object_or_404(ServiceRequest,tracking_number=tracking); form=StatusForm(request.POST or None,request.FILES or None,instance=item)
    if request.method=="POST" and form.is_valid():
        item=form.save(); RequestHistory.objects.create(request=item,status=item.status,remarks=item.staff_remarks,actor=request.user); Notification.objects.create(recipient=item.requester,title=f"Request {item.get_status_display()}",message=f"Your request {item.tracking_number} status was updated.",link=f"/services/{item.tracking_number}/"); record_action(request,"Service request status updated",item,current={"status":item.status}); return redirect("services:detail",tracking)
    return render(request,"services/update.html",{"form":form,"item":item})
def track(request):
    number=request.GET.get("number"); return render(request,"services/track.html",{"item":ServiceRequest.objects.filter(tracking_number=number).first() if number else None})

@login_required
def cancel(request,tracking):
    item=get_object_or_404(ServiceRequest,tracking_number=tracking,requester=request.user)
    if request.method=="POST" and item.status in {ServiceRequest.Status.SUBMITTED,ServiceRequest.Status.CORRECTION}:
        item.status=ServiceRequest.Status.CANCELLED; item.save(update_fields=["status","updated_at"])
        RequestHistory.objects.create(request=item,status=item.status,remarks="Cancelled by requester",actor=request.user)
        record_action(request,"Service request cancelled",item); return redirect("services:detail",tracking)
    raise PermissionDenied

@login_required
def attachment_download(request,pk):
    attachment=get_object_or_404(RequestAttachment.objects.select_related("request"),pk=pk)
    if attachment.request.requester_id!=request.user.id and not request.user.is_staff_member: raise PermissionDenied
    return FileResponse(attachment.file.open("rb"),as_attachment=True,filename=f"request-attachment-{attachment.pk}")

@login_required
def result_download(request,tracking):
    item=get_object_or_404(ServiceRequest,tracking_number=tracking)
    if item.requester_id!=request.user.id and not request.user.is_staff_member: raise PermissionDenied
    if not item.result_file: raise PermissionDenied
    return FileResponse(item.result_file.open("rb"),as_attachment=True,filename=f"{item.tracking_number}-result")
