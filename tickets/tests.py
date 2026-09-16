from django.test import TestCase, override_settings
from django.urls import reverse
from accounts.models import User
from .models import Ticket

@override_settings(ENABLE_ONLINE_TRANSACTIONS=True)
class TicketTests(TestCase):
    def setUp(self):
        self.owner=User.objects.create_user("owner",password="StrongPass!234")
        self.other=User.objects.create_user("other",password="StrongPass!234")
        self.ticket=Ticket.objects.create(number="TKT-TEST",subject="Concern",category="ICT",description="Details",requester=self.owner)

    def test_ticket_is_private(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("tickets:detail",args=[self.ticket.pk])).status_code,403)

    def test_owner_can_reply(self):
        self.client.force_login(self.owner)
        response=self.client.post(reverse("tickets:detail",args=[self.ticket.pk]),{"message":"Additional details"})
        self.assertEqual(response.status_code,302)
        self.assertEqual(self.ticket.replies.count(),1)
