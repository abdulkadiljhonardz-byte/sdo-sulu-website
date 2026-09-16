from django.contrib import admin
from .models import Complaint, ContactInquiry, Feedback
admin.site.register([Feedback, Complaint, ContactInquiry])
