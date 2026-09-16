from datetime import time,timedelta
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from offices.models import Office
from services.models import Service
from .models import Appointment,AppointmentSchedule

@override_settings(ENABLE_ONLINE_TRANSACTIONS=True)
class AppointmentTests(TestCase):
    def setUp(self):
        self.office=Office.objects.create(name="Records",code="records")
        self.service=Service.objects.create(name="Certification",office=self.office)
        self.date=timezone.localdate()+timedelta(days=1)
        self.slot=AppointmentSchedule.objects.create(office=self.office,weekday=self.date.weekday(),start_time=time(9),end_time=time(10),capacity=1)
        self.user1=User.objects.create_user("user1",password="StrongPass!234")
        self.user2=User.objects.create_user("user2",password="StrongPass!234")

    def payload(self):
        return {"office":self.office.pk,"service":self.service.pk,"date":self.date.isoformat(),"slot":self.slot.pk,"purpose":"Records request"}

    def test_capacity_prevents_double_booking(self):
        self.client.force_login(self.user1)
        self.assertEqual(self.client.post(reverse("appointments:index"),self.payload()).status_code,302)
        self.client.force_login(self.user2)
        response=self.client.post(reverse("appointments:index"),self.payload())
        self.assertEqual(response.status_code,200)
        self.assertEqual(Appointment.objects.count(),1)

    def test_user_cannot_cancel_another_users_appointment(self):
        item=Appointment.objects.create(reference_number="APT-TEST",user=self.user1,office=self.office,service=self.service,date=self.date,slot=self.slot,purpose="Test")
        self.client.force_login(self.user2)
        self.assertEqual(self.client.post(reverse("appointments:cancel",args=[item.pk])).status_code,403)
