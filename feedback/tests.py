from django.test import TestCase
from django.urls import reverse
from .models import Complaint,Feedback

class FeedbackTests(TestCase):
    def test_anonymous_feedback_discards_email(self):
        response=self.client.post(reverse("feedback:index"),{"action":"feedback","feedback-rating":5,"feedback-message":"Excellent","feedback-anonymous":"on","feedback-email":"person@example.com"})
        self.assertEqual(response.status_code,302)
        self.assertEqual(Feedback.objects.get().email,"")

    def test_complaint_receives_reference(self):
        response=self.client.post(reverse("feedback:index"),{"action":"complaint","complaint-subject":"Service concern","complaint-details":"Details","complaint-email":"person@example.com"})
        self.assertEqual(response.status_code,302)
        self.assertTrue(Complaint.objects.get().reference_number.startswith("CMP-"))
