from django import forms
from core.validators import validate_secure_upload
from .models import Ticket,TicketReply

class TicketForm(forms.ModelForm):
    class Meta:
        model=Ticket; fields=("subject","category","description","priority")
        widgets={"description":forms.Textarea(attrs={"rows":4})}

class TicketReplyForm(forms.ModelForm):
    class Meta:
        model=TicketReply; fields=("message","attachment")
        widgets={"message":forms.Textarea(attrs={"rows":3})}
    def clean_attachment(self):
        upload=self.cleaned_data.get("attachment")
        if upload: validate_secure_upload(upload)
        return upload
