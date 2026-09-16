from django import forms
from django.contrib.auth.forms import SetPasswordForm, UserCreationForm
from offices.models import Office
from .models import Role, StaffProfile, User


MANAGED_ROLE_CHOICES = [
    choice for choice in Role.choices if choice[0] != Role.SUPER_ADMIN
]

class RegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if not email:
            raise forms.ValidationError("An email address is required.")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account already uses this email address.")
        return email


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone")

    def __init__(self, *args, **kwargs):
        self.user = kwargs.get("instance")
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("Another account already uses this email address.")
        return email


class ManagedUserCreateForm(UserCreationForm):
    role = forms.ChoiceField(choices=MANAGED_ROLE_CHOICES)
    office = forms.ModelChoiceField(queryset=Office.objects.filter(active=True), required=False)
    position = forms.CharField(max_length=160, required=False)

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "role",
            "is_active",
            "office",
            "position",
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if not email:
            raise forms.ValidationError("An email address is required.")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account already uses this email address.")
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("role") == Role.STAFF and not cleaned.get("office"):
            self.add_error("office", "Office/Section Staff must be assigned to an office.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit)
        if commit:
            StaffProfile.objects.update_or_create(
                user=user,
                defaults={
                    "office": self.cleaned_data.get("office"),
                    "position": self.cleaned_data.get("position", ""),
                },
            )
        return user


class ManagedUserUpdateForm(forms.ModelForm):
    role = forms.ChoiceField(choices=MANAGED_ROLE_CHOICES)
    office = forms.ModelChoiceField(queryset=Office.objects.filter(active=True), required=False)
    position = forms.CharField(max_length=160, required=False)

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "phone",
            "role",
            "is_active",
            "office",
            "position",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        profile = getattr(self.instance, "staff_profile", None)
        if profile:
            self.fields["office"].initial = profile.office
            self.fields["position"].initial = profile.position

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if not email:
            raise forms.ValidationError("An email address is required.")
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Another account already uses this email address.")
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("role") == Role.STAFF and not cleaned.get("office"):
            self.add_error("office", "Office/Section Staff must be assigned to an office.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit)
        if commit:
            StaffProfile.objects.update_or_create(
                user=user,
                defaults={
                    "office": self.cleaned_data.get("office"),
                    "position": self.cleaned_data.get("position", ""),
                },
            )
        return user


class ManagedUserPasswordForm(SetPasswordForm):
    pass
