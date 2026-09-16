from django.db import models
from offices.models import District, TimeStampedModel

class School(TimeStampedModel):
    school_id = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=255)
    district = models.ForeignKey(District, on_delete=models.PROTECT, related_name="schools")
    school_type = models.CharField(max_length=80, blank=True)
    level = models.CharField(max_length=80, blank=True)
    classification = models.CharField(max_length=20, choices=[("PUBLIC", "Public"), ("PRIVATE", "Private")])
    school_head = models.CharField(max_length=160, blank=True)
    address = models.TextField(blank=True)
    barangay = models.CharField(max_length=100, blank=True)
    municipality = models.CharField(max_length=100, blank=True)
    contact_number = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    status = models.CharField(max_length=20, default="ACTIVE")
    student_population = models.PositiveIntegerField(null=True, blank=True)
    teacher_population = models.PositiveIntegerField(null=True, blank=True)
    class Meta: ordering = ["name"]
    def __str__(self): return self.name
