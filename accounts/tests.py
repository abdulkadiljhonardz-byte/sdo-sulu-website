from django.test import TestCase, override_settings
from django.urls import reverse
from .models import Role,User

class AccountTests(TestCase):
    google_settings = {
        "google": {
            "APPS": [
                {
                    "client_id": "test-client.apps.googleusercontent.com",
                    "secret": "test-secret",
                    "key": "",
                }
            ],
            "SCOPE": ["profile", "email"],
            "OAUTH_PKCE_ENABLED": True,
            "VERIFIED_EMAIL": True,
        }
    }

    def test_superuser_receives_super_admin_role(self):
        user=User.objects.create_superuser("root","root@example.com","StrongPass!234")
        self.assertEqual(user.role,Role.SUPER_ADMIN)
        self.assertTrue(user.is_verified)

    def test_login_accepts_email(self):
        User.objects.create_user("teacher",email="teacher@example.com",password="StrongPass!234")
        response=self.client.post(reverse("accounts:login"),{"username":"teacher@example.com","password":"StrongPass!234"})
        self.assertEqual(response.status_code,302)

    @override_settings(GOOGLE_LOGIN_ENABLED=True)
    def test_login_page_offers_google_sign_in(self):
        with self.settings(SOCIALACCOUNT_PROVIDERS=self.google_settings):
            response = self.client.get(reverse("accounts:login"))
        self.assertContains(response, "Continue with Google")

    def test_google_login_starts_with_post_and_redirects_to_google(self):
        with self.settings(SOCIALACCOUNT_PROVIDERS=self.google_settings):
            self.assertEqual(self.client.get(reverse("google_login")).status_code, 200)
            response = self.client.post(reverse("google_login"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("https://accounts.google.com/"))

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
