from django.contrib import admin
from .models import School

class SchoolAdmin(admin.ModelAdmin):
    list_display = ['school_id', 'name', 'district', 'classification', 'level']
    search_fields = ['school_id', 'name']
    list_filter = ['classification', 'level', 'status']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('school_id', 'name', 'school_type', 'level', 'classification')
        }),
        ('Location', {
            'fields': ('district', 'address', 'barangay', 'municipality', 'latitude', 'longitude')
        }),
        ('Contact & Personnel', {
            'fields': ('contact_number', 'email', 'school_head')
        }),
        ('Population', {
            'fields': ('student_population', 'teacher_population')
        }),
        ('Status', {
            'fields': ('status', 'created_at', 'updated_at')
        }),
    )

admin.site.register(School, SchoolAdmin)

