from django.test import TestCase
from django.urls import reverse
from content.models import PublicPage

from .models import Complaint, ContactInquiry, Feedback

class FeedbackTests(TestCase):
    def setUp(self):
        PublicPage.objects.get_or_create(
            slug="contact",
            defaults={
                "title": "Contact",
                "body": "Contact SDO Sulu.",
                "published": True,
            },
        )

    def test_anonymous_feedback_discards_email(self):
        response=self.client.post(reverse("feedback:index"),{"action":"feedback","feedback-rating":5,"feedback-message":"Excellent","feedback-anonymous":"on","feedback-email":"person@example.com"})
        self.assertEqual(response.status_code,302)
        self.assertEqual(Feedback.objects.get().email,"")

    def test_complaint_receives_reference(self):
        response=self.client.post(reverse("feedback:index"),{"action":"complaint","complaint-subject":"Service concern","complaint-details":"Details","complaint-email":"person@example.com"})
        self.assertEqual(response.status_code,302)
        self.assertTrue(Complaint.objects.get().reference_number.startswith("CMP-"))

    def test_contact_page_saves_private_inquiry(self):
        response = self.client.post(
            reverse("pages:contact"),
            {
                "name": "Juan Dela Cruz",
                "email": "juan@example.com",
                "phone": "0965 000 0000",
                "address": "Jolo, Sulu",
                "message": "Please help me with my public inquiry.",
                "website": "",
            },
        )
        self.assertRedirects(response, reverse("pages:contact"))
        inquiry = ContactInquiry.objects.get()
        self.assertEqual(inquiry.name, "Juan Dela Cruz")
        self.assertEqual(inquiry.status, ContactInquiry.Status.NEW)

    def test_contact_honeypot_rejects_bot_submission(self):
        response = self.client.post(
            reverse("pages:contact"),
            {
                "name": "Bot",
                "email": "bot@example.com",
                "phone": "09650000000",
                "message": "This looks like a valid inquiry.",
                "website": "https://spam.example",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ContactInquiry.objects.exists())
