from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models


class Role(models.TextChoices):
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
    ADMIN = "ADMIN", "SDO Administrator"
    STAFF = "STAFF", "Office / Section Staff"
    SCHOOL_HEAD = "SCHOOL_HEAD", "School Head"
    USER = "USER", "Registered User"


class UserManager(DjangoUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", Role.SUPER_ADMIN)
        extra_fields.setdefault("is_verified", True)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    phone = models.CharField(max_length=32, blank=True)
    is_verified = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = UserManager()

    @property
    def is_staff_member(self):
        return self.role in {Role.SUPER_ADMIN, Role.ADMIN, Role.STAFF}


class StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="staff_profile")
    office = models.ForeignKey("offices.Office", null=True, blank=True, on_delete=models.SET_NULL)
    position = models.CharField(max_length=160, blank=True)
