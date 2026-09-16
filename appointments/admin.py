from django.contrib import admin
from .models import Appointment,AppointmentSchedule
admin.site.register([Appointment,AppointmentSchedule])
