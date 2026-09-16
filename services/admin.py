from django.contrib import admin
from .models import Service,ServiceRequirement,ServiceRequest,RequestAttachment,RequestHistory
admin.site.register([Service,ServiceRequirement,ServiceRequest,RequestAttachment,RequestHistory])
