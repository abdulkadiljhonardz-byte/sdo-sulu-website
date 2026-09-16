from django.test import TestCase
from django.urls import reverse
from .models import Role,User

class AccountTests(TestCase):
    def test_superuser_receives_super_admin_role(self):
        user=User.objects.create_superuser("root","root@example.com","StrongPass!234")
        self.assertEqual(user.role,Role.SUPER_ADMIN)
        self.assertTrue(user.is_verified)

    def test_login_accepts_email(self):
        User.objects.create_user("teacher",email="teacher@example.com",password="StrongPass!234")
        response=self.client.post(reverse("accounts:login"),{"username":"teacher@example.com","password":"StrongPass!234"})
        self.assertEqual(response.status_code,302)

    def test_profile_requires_authentication(self):
        response=self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code,302)

    def test_repeated_failed_logins_are_rate_limited(self):
        for _ in range(5):
            self.client.post(reverse("accounts:login"),{"username":"unknown","password":"wrong"})
        response=self.client.post(reverse("accounts:login"),{"username":"unknown","password":"wrong"})
        self.assertEqual(response.status_code,429)

    def test_only_super_admin_can_open_user_management(self):
        ordinary = User.objects.create_user(
            "ordinary", email="ordinary@example.com", password="StrongPass!234"
        )
        self.client.force_login(ordinary)
        response = self.client.get(reverse("accounts:user_management"))
        self.assertEqual(response.status_code, 403)

    def test_super_admin_can_create_sdo_administrator(self):
        super_admin = User.objects.create_superuser(
            "rootadmin", "rootadmin@example.com", "StrongPass!234"
        )
        self.client.force_login(super_admin)
        response = self.client.post(
            reverse("accounts:user_create"),
            {
                "username": "divisionadmin",
                "first_name": "Division",
                "last_name": "Administrator",
                "email": "divisionadmin@example.com",
                "phone": "",
                "role": Role.ADMIN,
                "is_active": "on",
                "password1": "AnotherStrong!234",
                "password2": "AnotherStrong!234",
            },
        )
        self.assertRedirects(response, reverse("accounts:user_management"))
        created = User.objects.get(username="divisionadmin")
        self.assertEqual(created.role, Role.ADMIN)
        self.assertTrue(created.is_staff)
        self.assertFalse(created.is_superuser)
        self.assertTrue(created.user_permissions.exists())
