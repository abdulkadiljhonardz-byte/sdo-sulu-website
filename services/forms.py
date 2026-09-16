from django import forms
from accounts.models import User
from core.validators import validate_secure_upload
from .models import ServiceRequest

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected=True

class MultipleFileField(forms.FileField):
    def clean(self,data,initial=None):
        single=super().clean
        return [single(item,initial) for item in (data if isinstance(data,(list,tuple)) else [data])] if data else []

class ServiceRequestForm(forms.ModelForm):
    attachments=MultipleFileField(required=False,widget=MultipleFileInput(attrs={"accept":".pdf,.jpg,.jpeg,.png,.docx,.xlsx"}))
    class Meta: model=ServiceRequest; fields=["service","purpose"]
    def clean_attachments(self):
        files=self.cleaned_data.get("attachments",[])
        for upload in files: validate_secure_upload(upload)
        return files
class StatusForm(forms.ModelForm):
    TRANSITIONS={"SUBMITTED":{"REVIEW","CANCELLED"},"REVIEW":{"PROCESSING","CORRECTION","REJECTED"},"PROCESSING":{"APPROVAL","CORRECTION","REJECTED"},"APPROVAL":{"APPROVED","REJECTED","CORRECTION"},"APPROVED":{"READY"},"READY":{"RELEASED"},"CORRECTION":{"REVIEW","CANCELLED"}}
    class Meta: model=ServiceRequest; fields=["status","staff_remarks","assigned_to","result_file"]
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["assigned_to"].queryset=User.objects.filter(role__in=["SUPER_ADMIN","ADMIN","STAFF"],is_active=True)
    def clean_result_file(self):
        upload=self.cleaned_data.get("result_file")
        if upload: validate_secure_upload(upload)
        return upload
    def clean_status(self):
        status=self.cleaned_data["status"]
        if self.instance.pk and status!=self.instance.status and status not in self.TRANSITIONS.get(self.instance.status,set()):
            label=dict(ServiceRequest.Status.choices).get(status,status)
            raise forms.ValidationError(f"Cannot change status from {self.instance.get_status_display()} to {label}.")
        return status
