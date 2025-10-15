from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    ROLE_TEACHER = 'teacher'
    ROLE_STUDENT = 'student'
    ROLE_CHOICES = (
        (ROLE_TEACHER, 'Teacher'),
        (ROLE_STUDENT, 'Student'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self) -> str:
        return f"{self.user.username} ({self.role})"

from django.db import models

# Create your models here.
