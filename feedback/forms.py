from django import forms
from .models import Complaint, ContactInquiry, Feedback


class ContactInquiryForm(forms.ModelForm):
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
    )

    class Meta:
        model = ContactInquiry
        fields = ("name", "email", "phone", "address", "message")
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Your name", "autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"placeholder": "Your email address", "autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"placeholder": "Phone number", "autocomplete": "tel", "inputmode": "tel"}),
            "address": forms.TextInput(attrs={"placeholder": "Your address (optional)", "autocomplete": "street-address"}),
            "message": forms.Textarea(attrs={"placeholder": "How can we help you?", "rows": 7}),
        }

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Invalid submission.")
        return ""

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        digits = "".join(character for character in phone if character.isdigit())
        if len(digits) < 7 or len(digits) > 15:
            raise forms.ValidationError("Enter a valid contact number.")
        return phone

    def clean_message(self):
        message = self.cleaned_data["message"].strip()
        if len(message) < 10:
            raise forms.ValidationError("Please provide at least 10 characters.")
        return message

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
