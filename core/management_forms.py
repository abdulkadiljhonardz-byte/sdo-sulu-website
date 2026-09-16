from pathlib import Path

from django import forms
from django.utils import timezone
from django.utils.text import slugify

from content.models import Download, News, PublicPage
from core.validators import (
    MAX_UPLOAD_SIZE,
    validate_secure_image_upload,
    validate_secure_upload,
)
from events.models import Event
from issuances.models import Issuance
from offices.models import District, Office
from schools.models import School
from vacancies.models import Vacancy
from verification.models import VerifiedDocument
from feedback.models import Complaint, ContactInquiry
from notifications.models import Notification
from content.facebook_import import validate_facebook_url


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "management-input")


class PublicationForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "cover_image" in self.fields:
            self.fields["cover_image"].help_text = (
                "Upload a JPG or PNG cover photo (maximum 10 MB)."
            )
        if "source_url" in self.fields:
            self.fields["source_url"].help_text = (
                "Optional: link this item to its original public Facebook post."
            )

    def clean_cover_image(self):
        upload = self.cleaned_data.get("cover_image")
        if upload and not getattr(upload, "_committed", False):
            validate_secure_image_upload(upload)
        return upload

    def save(self, commit=True):
        item = super().save(commit=False)
        if not item.slug:
            base = slugify(item.title)[:45] or "publication"
            candidate = base
            index = 2
            model = item.__class__
            while model.objects.filter(slug=candidate).exclude(pk=item.pk).exists():
                candidate = f"{base}-{index}"
                index += 1
            item.slug = candidate
        if item.is_published and not item.published_at:
            item.published_at = timezone.now()
        if commit:
            item.save()
            self.save_m2m()
        return item

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("expires_at") and cleaned.get("published_at") and cleaned["expires_at"] <= cleaned["published_at"]:
            self.add_error("expires_at", "Expiration must be later than the scheduled publication time.")
        return cleaned

    def clean_source_url(self):
        source_url = self.cleaned_data.get("source_url", "").strip()
        if source_url:
            source_url = validate_facebook_url(source_url)
            model = self._meta.model
            if model.objects.filter(source_url__iexact=source_url).exclude(
                pk=self.instance.pk
            ).exists():
                raise forms.ValidationError(
                    "This Facebook post is already linked to another item."
                )
        return source_url


class NewsManagementForm(PublicationForm):
    class Meta:
        model = News
        fields = ("title", "body", "category", "office", "cover_image", "source_url", "published_at", "expires_at", "is_published", "is_featured", "archived")
        widgets = {"published_at": forms.DateTimeInput(attrs={"type": "datetime-local"}), "expires_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}


class FacebookImportForm(forms.Form):
    facebook_url = forms.URLField(
        label="Public Facebook post link",
        max_length=1000,
        widget=forms.URLInput(
            attrs={
                "class": "management-input",
                "placeholder": "https://www.facebook.com/.../posts/...",
                "autocomplete": "off",
            }
        ),
    )
    publish_now = forms.BooleanField(
        required=False,
        initial=True,
        label="Publish immediately after import",
        help_text="Administrators can publish immediately. Office Staff imports still require administrator review.",
    )

    def clean_facebook_url(self):
        value = self.cleaned_data["facebook_url"].strip()
        return validate_facebook_url(value)


class DownloadManagementForm(StyledModelForm):
    class Meta:
        model = Download
        fields = ("title", "category", "office", "description", "file", "publish_at", "expires_at", "published", "archived")
        widgets = {"publish_at": forms.DateTimeInput(attrs={"type": "datetime-local"}), "expires_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}

    def clean_file(self):
        upload = self.cleaned_data.get("file")
        if upload and not getattr(upload, "_committed", False):
            validate_secure_upload(upload)
        return upload

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("expires_at") and cleaned.get("publish_at") and cleaned["expires_at"] <= cleaned["publish_at"]:
            self.add_error("expires_at", "Expiration must be later than the scheduled publication time.")
        return cleaned


class IssuanceManagementForm(StyledModelForm):
    status = forms.ChoiceField(choices=[
        ("DRAFT", "Draft"),
        ("PENDING_REVIEW", "Pending Review"),
        ("PUBLISHED", "Published"),
        ("ARCHIVED", "Archived"),
    ])
    revision_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Required when replacing an existing PDF.",
    )
    class Meta:
        model = Issuance
        fields = ("category", "reference_number", "title", "year", "date_issued", "office", "cover_image", "pdf", "source_url", "status", "publish_at", "expires_at", "is_featured", "keywords", "archived")
        widgets = {"date_issued": forms.DateInput(attrs={"type": "date"}), "publish_at": forms.DateTimeInput(attrs={"type": "datetime-local"}), "expires_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cover_image"].help_text = (
            "Required for new memoranda. Upload a JPG or PNG display picture (maximum 10 MB)."
        )
        self.fields["pdf"].help_text = "Upload the complete official memorandum as a valid PDF."
        self.fields["source_url"].help_text = (
            "If no PDF is available, link the original post from the official SDO Facebook Page."
        )

    def clean_cover_image(self):
        upload = self.cleaned_data.get("cover_image")
        if upload and not getattr(upload, "_committed", False):
            validate_secure_image_upload(upload)
        if not upload and not self.instance.pk:
            raise forms.ValidationError("Upload a cover picture for this memorandum.")
        return upload

    def clean_pdf(self):
        upload = self.cleaned_data.get("pdf")
        if upload and not getattr(upload, "_committed", False):
            validate_secure_upload(upload)
            if Path(upload.name).suffix.lower() != ".pdf":
                raise forms.ValidationError("Official issuances must be uploaded as PDF files.")
            signature = upload.read(5)
            upload.seek(0)
            if signature != b"%PDF-":
                raise forms.ValidationError("The uploaded file is not a valid PDF document.")
        return upload

    def clean_source_url(self):
        source_url = self.cleaned_data.get("source_url", "").strip()
        if source_url:
            source_url = validate_facebook_url(source_url)
            if Issuance.objects.filter(source_url__iexact=source_url).exclude(
                pk=self.instance.pk
            ).exists():
                raise forms.ValidationError(
                    "This Facebook post is already linked to another issuance."
                )
        return source_url

    def clean(self):
        cleaned = super().clean()
        uploaded = self.files.get("pdf")
        if not cleaned.get("pdf") and not cleaned.get("source_url") and not self.instance.pk:
            self.add_error(
                "pdf",
                "Upload the official PDF or provide the original official Facebook post link.",
            )
        if self.instance.pk and uploaded and not cleaned.get("revision_reason", "").strip():
            self.add_error("revision_reason", "Explain why the official document is being replaced.")
        reference = cleaned.get("reference_number", "").strip()
        if reference and Issuance.objects.filter(reference_number__iexact=reference).exclude(pk=self.instance.pk).exists():
            self.add_error("reference_number", "An issuance already uses this reference number.")
        if cleaned.get("expires_at") and cleaned.get("publish_at") and cleaned["expires_at"] <= cleaned["publish_at"]:
            self.add_error("expires_at", "Expiration must be later than the scheduled publication time.")
        return cleaned


class EventManagementForm(StyledModelForm):
    class Meta:
        model = Event
        fields = ("title", "description", "office", "start", "end", "location", "organizer", "category")
        widgets = {"start": forms.DateTimeInput(attrs={"type": "datetime-local"}), "end": forms.DateTimeInput(attrs={"type": "datetime-local"})}

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("end") and cleaned.get("start") and cleaned["end"] < cleaned["start"]:
            self.add_error("end", "The end time cannot be earlier than the start time.")
        return cleaned


class VacancyManagementForm(StyledModelForm):
    class Meta:
        model = Vacancy
        fields = ("position", "office", "employment_type", "salary_grade", "qualification", "education", "experience", "training", "eligibility", "requirements", "posting_date", "deadline", "status")
        widgets = {"posting_date": forms.DateInput(attrs={"type": "date"}), "deadline": forms.DateInput(attrs={"type": "date"})}

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("deadline") and cleaned.get("posting_date") and cleaned["deadline"] < cleaned["posting_date"]:
            self.add_error("deadline", "The deadline cannot be earlier than the posting date.")
        return cleaned


class SchoolManagementForm(StyledModelForm):
    class Meta:
        model = School
        fields = ("school_id", "name", "district", "school_type", "level", "classification", "school_head", "address", "barangay", "municipality", "contact_number", "email", "latitude", "longitude", "status", "student_population", "teacher_population")


class OfficeManagementForm(StyledModelForm):
    class Meta:
        model = Office
        fields = ("name", "code", "email", "phone", "description", "active")


class DistrictManagementForm(StyledModelForm):
    class Meta:
        model = District
        fields = ("name", "municipality", "public_school_target", "active")


class VerifiedDocumentManagementForm(StyledModelForm):
    class Meta:
        model = VerifiedDocument
        fields = ("document_number", "recipient", "document_type", "issuing_office", "date_issued", "status")
        widgets = {"date_issued": forms.DateInput(attrs={"type": "date"})}


class PublicPageManagementForm(StyledModelForm):
    protected_slugs = {
        "about", "mission", "vision", "core-values", "officials",
        "organizational-structure", "citizens-charter", "privacy-policy",
        "terms-of-use",
    }
    class Meta:
        model = PublicPage
        fields = ("slug", "title", "summary", "body", "image", "published")

    def clean_image(self):
        upload = self.cleaned_data.get("image")
        if upload and not getattr(upload, "_committed", False):
            validate_secure_image_upload(upload)
        return upload

    def clean_slug(self):
        slug = self.cleaned_data["slug"]
        if self.instance.pk and self.instance.slug in self.protected_slugs and slug != self.instance.slug:
            raise forms.ValidationError("This system page URL cannot be changed.")
        return slug


class ContactInquiryManagementForm(StyledModelForm):
    class Meta:
        model = ContactInquiry
        fields = ("status",)


class PortalSettingsForm(forms.Form):
    sdo_name = forms.CharField(max_length=200, label="Official SDO name")
    address = forms.CharField(max_length=255)
    email = forms.EmailField()
    phone = forms.CharField(max_length=40)
    whatsapp = forms.CharField(
        max_length=40,
        required=False,
        label="WhatsApp number",
        help_text="Include the country code, for example +63 966 175 6976.",
    )
    map_url = forms.URLField(
        required=False,
        label="Google Maps location link",
        help_text="Use the official Google Maps place or pin URL for the office.",
    )
    office_hours = forms.CharField(max_length=160, required=False)
    homepage_banner = forms.CharField(widget=forms.Textarea, required=False)
    footer_text = forms.CharField(max_length=255, required=False)
    maintenance_mode = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "management-input")


class ComplaintManagementForm(StyledModelForm):
    status = forms.ChoiceField(
        choices=[
            ("OPEN", "Open"),
            ("UNDER_REVIEW", "Under Review"),
            ("RESPONDED", "Responded"),
            ("CLOSED", "Closed"),
        ]
    )

    class Meta:
        model = Complaint
        fields = ("status",)


class NotificationManagementForm(StyledModelForm):
    class Meta:
        model = Notification
        fields = ("recipient", "title", "message", "link")


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        cleaner = super().clean
        if isinstance(data, (list, tuple)):
            return [cleaner(item, initial) for item in data]
        return [cleaner(data, initial)] if data else []


class BulkImportForm(forms.Form):
    DATASET_CHOICES = [("schools", "Schools"), ("issuances", "Issuances & Memoranda")]
    dataset = forms.ChoiceField(choices=DATASET_CHOICES)
    spreadsheet = forms.FileField(help_text="Upload a CSV or XLSX file using the provided column template.")
    pdf_files = MultipleFileField(required=False, help_text="For issuance imports, attach every PDF named in the pdf_filename column.")

    def clean_spreadsheet(self):
        upload = self.cleaned_data["spreadsheet"]
        if Path(upload.name).suffix.lower() not in {".csv", ".xlsx"}:
            raise forms.ValidationError("Import files must use CSV or XLSX format.")
        if upload.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError("Import files must not exceed 10 MB.")
        return upload

    def clean(self):
        cleaned = super().clean()
        files = cleaned.get("pdf_files") or []
        if len(files) > 500:
            self.add_error("pdf_files", "A single import may contain at most 500 PDFs.")
        if sum(getattr(item, "size", 0) for item in files) > 100 * 1024 * 1024:
            self.add_error("pdf_files", "Combined PDF uploads must not exceed 100 MB.")
        if cleaned.get("dataset") == "issuances" and not files:
            self.add_error("pdf_files", "Attach the PDFs referenced by the issuance spreadsheet.")
        return cleaned


class ReportFilterForm(forms.Form):
    REPORT_CHOICES = [
        ("issuances", "Issuances"), ("schools", "Schools"),
        ("news", "News"), ("complaints", "Complaints"),
        ("staff", "Active staff"), ("analytics", "Portal analytics"),
    ]
    report = forms.ChoiceField(choices=REPORT_CHOICES)
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("date_from") and cleaned.get("date_to") and cleaned["date_to"] < cleaned["date_from"]:
            self.add_error("date_to", "End date cannot be earlier than start date.")
        return cleaned
