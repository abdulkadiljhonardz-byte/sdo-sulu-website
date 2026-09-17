from django.contrib import admin
from .models import School

class SchoolAdmin(admin.ModelAdmin):
    list_display = ['school_id', 'name', 'district', 'status']
    search_fields = ['school_id', 'name']
    list_filter = ['status', 'classification', 'district']

admin.site.register(School, SchoolAdmin)

