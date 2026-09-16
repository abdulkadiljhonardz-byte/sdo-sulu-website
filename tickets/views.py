import uuid
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import get_object_or_404,redirect,render
from audit.utils import record_action
from notifications.models import Notification
from .forms import TicketForm,TicketReplyForm
from .models import Ticket

@login_required
def index(request):
    form=TicketForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        item=form.save(commit=False); item.requester=request.user; item.number=f"TKT-{uuid.uuid4().hex[:10].upper()}"; item.save()
        record_action(request,"Help desk ticket created",item,current={"number":item.number}); messages.success(request,f"Ticket {item.number} was submitted."); return redirect("tickets:detail",item.pk)
    items=Ticket.objects.filter(requester=request.user).order_by("-created_at")
    return render(request,"tickets/index.html",{"form":form,"tickets":items})

@login_required
def detail(request,pk):
    item=get_object_or_404(Ticket,pk=pk)
    if item.requester_id!=request.user.id and not request.user.is_staff_member: raise PermissionDenied
    form=TicketReplyForm(request.POST or None,request.FILES or None)
    if request.method=="POST" and form.is_valid():
        reply=form.save(commit=False); reply.ticket=item; reply.author=request.user; reply.save()
        if request.user.is_staff_member and item.requester_id!=request.user.id:
            Notification.objects.create(recipient=item.requester,title=f"Reply to {item.number}",message="A staff member replied to your help desk ticket.",link=f"/helpdesk/{item.pk}/")
        record_action(request,"Ticket reply added",item); messages.success(request,"Your reply was added."); return redirect("tickets:detail",item.pk)
    replies=item.replies.select_related("author")
    if not request.user.is_staff_member: replies=replies.filter(internal=False)
    return render(request,"tickets/detail.html",{"item":item,"replies":replies,"form":form})

@login_required
def attachment(request,pk):
    from .models import TicketReply
    reply=get_object_or_404(TicketReply.objects.select_related("ticket"),pk=pk)
    if reply.ticket.requester_id!=request.user.id and not request.user.is_staff_member: raise PermissionDenied
    if not reply.attachment: raise PermissionDenied
    return FileResponse(reply.attachment.open("rb"),as_attachment=True,filename=f"ticket-attachment-{reply.pk}")
