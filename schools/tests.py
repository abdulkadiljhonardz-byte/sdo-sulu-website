from django.db.models import Sum
from django.test import TestCase
from django.urls import reverse

from offices.models import District

from .models import School


class SchoolDirectoryTests(TestCase):
    def test_seeded_public_school_targets_total_457(self):
        districts = District.objects.filter(active=True)
        self.assertEqual(districts.count(), 20)
        self.assertEqual(
            districts.aggregate(total=Sum("public_school_target"))["total"],
            457,
        )

    def test_directory_shows_target_and_filters_schools_by_district(self):
        indanan = District.objects.get(name="Indanan")
        jolo = District.objects.get(name="Jolo I")
        School.objects.create(
            school_id="SULU-001",
            name="Indanan Sample School",
            district=indanan,
            municipality="Indanan",
            classification="PUBLIC",
        )
        School.objects.create(
            school_id="SULU-002",
            name="Jolo Sample School",
            district=jolo,
            municipality="Jolo",
            classification="PUBLIC",
        )

        response = self.client.get(
            reverse("schools:directory"), {"district": indanan.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_target"], 457)
        self.assertContains(response, "Indanan Sample School")
        self.assertNotContains(response, "Jolo Sample School")
