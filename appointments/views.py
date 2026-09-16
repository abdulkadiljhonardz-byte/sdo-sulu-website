import uuid
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404,redirect,render
from audit.utils import record_action
from .forms import AppointmentForm
from .models import Appointment,AppointmentSchedule

@login_required
def index(request):
    form=AppointmentForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        with transaction.atomic():
            slot=AppointmentSchedule.objects.select_for_update().get(pk=form.cleaned_data["slot"].pk)
            booked=Appointment.objects.filter(slot=slot,date=form.cleaned_data["date"]).exclude(status__in=["REJECTED","CANCELLED"]).count()
            if booked>=slot.capacity: form.add_error("slot","This time slot is already fully booked.")
            else:
                item=form.save(commit=False); item.user=request.user; item.reference_number=f"APT-{uuid.uuid4().hex[:10].upper()}"; item.save()
                record_action(request,"Appointment created",item,current={"reference":item.reference_number}); messages.success(request,f"Appointment {item.reference_number} was submitted."); return redirect("appointments:index")
    items=Appointment.objects.filter(user=request.user).select_related("office","service","slot")
    return render(request,"appointments/index.html",{"form":form,"appointments":items})

@login_required
def cancel(request,pk):
    item=get_object_or_404(Appointment,pk=pk)
    if item.user_id!=request.user.id: raise PermissionDenied
    if request.method=="POST" and item.status in {"PENDING","APPROVED"}:
        item.status="CANCELLED"; item.save(update_fields=["status","updated_at"]); record_action(request,"Appointment cancelled",item); messages.success(request,"Appointment cancelled.")
    return redirect("appointments:index")

@login_required
def reschedule(request,pk):
    item=get_object_or_404(Appointment,pk=pk,user=request.user)
    if item.status not in {"PENDING","APPROVED"}: raise PermissionDenied
    form=AppointmentForm(request.POST or None,instance=item)
    if request.method=="POST" and form.is_valid():
        with transaction.atomic():
            slot=AppointmentSchedule.objects.select_for_update().get(pk=form.cleaned_data["slot"].pk)
            booked=Appointment.objects.filter(slot=slot,date=form.cleaned_data["date"]).exclude(pk=item.pk).exclude(status__in=["REJECTED","CANCELLED"]).count()
            if booked>=slot.capacity: form.add_error("slot","This time slot is already fully booked.")
            else: form.save(); record_action(request,"Appointment rescheduled",item); messages.success(request,"Appointment rescheduled."); return redirect("appointments:index")
    return render(request,"appointments/reschedule.html",{"form":form,"appointment":item})
