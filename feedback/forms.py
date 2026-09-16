from django import forms
from .models import Complaint,Feedback

class FeedbackForm(forms.ModelForm):
    class Meta:
        model=Feedback; fields=("rating","message","anonymous","email")
        widgets={"rating":forms.NumberInput(attrs={"min":1,"max":5}),"message":forms.Textarea(attrs={"rows":4})}
    def clean_rating(self):
        rating=self.cleaned_data.get("rating")
        if rating is not None and rating not in range(1,6): raise forms.ValidationError("Choose a rating from 1 to 5.")
        return rating
    def clean(self):
        data=super().clean()
        if data.get("anonymous"): data["email"]=""
        return data

class ComplaintForm(forms.ModelForm):
    class Meta:
        model=Complaint; fields=("subject","details","email")
        widgets={"details":forms.Textarea(attrs={"rows":5})}
