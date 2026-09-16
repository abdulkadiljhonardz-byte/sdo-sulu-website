from django import forms
from django.utils import timezone
from services.models import Service
from .models import Appointment, AppointmentSchedule

class AppointmentForm(forms.ModelForm):
    class Meta:
        model=Appointment; fields=("office","service","date","slot","purpose")
        widgets={"date":forms.DateInput(attrs={"type":"date"}),"purpose":forms.Textarea(attrs={"rows":3})}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["slot"].queryset=AppointmentSchedule.objects.filter(active=True).select_related("office")
        self.fields["service"].queryset=Service.objects.filter(active=True).select_related("office")
    def clean(self):
        data=super().clean(); office=data.get("office"); service=data.get("service"); date=data.get("date"); slot=data.get("slot")
        if date and date<timezone.localdate(): self.add_error("date","Appointments cannot be scheduled in the past.")
        if office and slot and slot.office_id!=office.id: self.add_error("slot","The selected time slot belongs to another office.")
        if service and office and service.office_id!=office.id: self.add_error("service","The selected service belongs to another office.")
        if date and slot and date.weekday()!=slot.weekday: self.add_error("date","The selected schedule is unavailable on this weekday.")
        return data
