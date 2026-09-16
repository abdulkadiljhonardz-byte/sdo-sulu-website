import uuid
from django.contrib import messages
from django.shortcuts import redirect,render
from audit.utils import record_action
from .forms import ComplaintForm,FeedbackForm

def index(request):
    feedback_form=FeedbackForm(prefix="feedback")
    complaint_form=ComplaintForm(prefix="complaint",initial={"email":request.user.email if request.user.is_authenticated else ""})
    if request.method=="POST":
        action=request.POST.get("action")
        if action=="feedback":
            feedback_form=FeedbackForm(request.POST,prefix="feedback")
            if feedback_form.is_valid():
                item=feedback_form.save(); record_action(request,"Feedback submitted",item); messages.success(request,"Thank you for your feedback."); return redirect("feedback:index")
        elif action=="complaint":
            complaint_form=ComplaintForm(request.POST,prefix="complaint")
            if complaint_form.is_valid():
                item=complaint_form.save(commit=False); item.reference_number=f"CMP-{uuid.uuid4().hex[:10].upper()}"; item.save(); record_action(request,"Complaint submitted",item); messages.success(request,f"Complaint received. Keep reference {item.reference_number}."); return redirect("feedback:index")
    return render(request,"feedback/index.html",{"feedback_form":feedback_form,"complaint_form":complaint_form})
