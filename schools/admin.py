from pathlib import Path

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from accounts.models import Role
from audit.utils import record_action
from core.data_tools import ImportValidationError, import_schools

from .models import School


class SchoolImportForm(forms.Form):
    spreadsheet = forms.FileField(
        label="CSV or Excel file",
        help_text="Use the school import template. Maximum file size: 10 MB.",
    )

    def clean_spreadsheet(self):
        upload = self.cleaned_data["spreadsheet"]
        if Path(upload.name).suffix.lower() not in {".csv", ".xlsx"}:
            raise forms.ValidationError("Upload a CSV or XLSX file.")
        if upload.size > 10 * 1024 * 1024:
            raise forms.ValidationError("The import file must not exceed 10 MB.")
        return upload


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    change_list_template = "admin/schools/school/change_list.html"
    list_display = ("school_id", "name", "district", "municipality", "classification", "status")
    list_filter = ("classification", "status", "district")
    search_fields = ("school_id", "name", "municipality", "barangay")
    list_select_related = ("district",)

    def has_import_permission(self, request):
        return request.user.is_superuser or request.user.role in {
            Role.SUPER_ADMIN,
            Role.ADMIN,
        }

    def changelist_view(self, request, extra_context=None):
        extra_context = {
            **(extra_context or {}),
            "can_import_schools": self.has_import_permission(request),
        }
        return super().changelist_view(request, extra_context=extra_context)

    def get_urls(self):
        return [
            path(
                "import/",
                self.admin_site.admin_view(self.import_view),
                name="schools_school_import",
            ),
        ] + super().get_urls()

    def import_view(self, request):
        if not self.has_change_permission(request) or not self.has_import_permission(request):
            raise PermissionDenied

        form = SchoolImportForm(request.POST or None, request.FILES or None)
        import_errors = []
        if request.method == "POST" and form.is_valid():
            try:
                result = import_schools(form.cleaned_data["spreadsheet"])
            except ImportValidationError as exc:
                import_errors = exc.errors
            else:
                record_action(request, "School directory bulk updated", current=result)
                self.message_user(
                    request,
                    f"Import complete: {result['created']} created, {result['updated']} updated.",
                    messages.SUCCESS,
                )
                return redirect(reverse("admin:schools_school_changelist"))

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Import schools",
            "form": form,
            "import_errors": import_errors,
        }
        return TemplateResponse(request, "admin/schools/school/import.html", context)
