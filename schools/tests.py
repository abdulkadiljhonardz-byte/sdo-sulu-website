from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Sum
from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User
from accounts.roles import synchronize_role_permissions
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

    def test_directory_is_simple_and_filters_schools_by_district(self):
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
        self.assertContains(response, "Indanan Sample School")
        self.assertNotContains(response, "Jolo Sample School")
        self.assertContains(response, "Find a school in Sulu.")
        self.assertNotContains(response, "Public-school targets")
        self.assertNotContains(response, "target total is calculated")


class SchoolAdminImportTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            "schooladmin",
            "schooladmin@example.com",
            "StrongPass!234",
        )
        self.client.force_login(self.admin)

    def test_school_admin_has_bulk_import_link(self):
        response = self.client.get(reverse("admin:schools_school_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Import CSV/Excel")

    def test_admin_can_import_school_csv(self):
        district = District.objects.get(name="Indanan")
        spreadsheet = SimpleUploadedFile(
            "schools.csv",
            (
                "school_id,name,district,classification,municipality\n"
                f"SULU-IMPORT-1,Imported School,{district.name},PUBLIC,Indanan\n"
            ).encode(),
            content_type="text/csv",
        )

        response = self.client.post(
            reverse("admin:schools_school_import"),
            {"spreadsheet": spreadsheet},
        )

        self.assertRedirects(response, reverse("admin:schools_school_changelist"))
        self.assertTrue(School.objects.filter(school_id="SULU-IMPORT-1").exists())

    def test_invalid_import_is_not_saved(self):
        spreadsheet = SimpleUploadedFile(
            "schools.csv",
            b"school_id,name,district,classification,municipality\nBAD-1,Bad School,Unknown,PUBLIC,Jolo\n",
            content_type="text/csv",
        )

        response = self.client.post(
            reverse("admin:schools_school_import"),
            {"spreadsheet": spreadsheet},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "unknown or inactive district Unknown")
        self.assertFalse(School.objects.filter(school_id="BAD-1").exists())

    def test_regular_staff_cannot_use_bulk_import(self):
        staff = User.objects.create_user(
            "schoolstaff",
            password="StrongPass!234",
            role=Role.STAFF,
        )
        synchronize_role_permissions(staff)
        self.client.force_login(staff)

        response = self.client.get(reverse("admin:schools_school_import"))

        self.assertEqual(response.status_code, 403)
