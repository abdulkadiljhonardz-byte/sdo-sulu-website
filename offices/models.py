from django.db import models

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: abstract = True

class Office(TimeStampedModel):
    name = models.CharField(max_length=200, unique=True)
    code = models.SlugField(unique=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    def __str__(self): return self.name

class District(TimeStampedModel):
    name = models.CharField(max_length=160, unique=True)
    municipality = models.CharField(max_length=160)
    public_school_target = models.PositiveIntegerField(
        default=0,
        help_text="Official target number of public schools for this district.",
    )
    active = models.BooleanField(default=True)
    def __str__(self): return self.name
