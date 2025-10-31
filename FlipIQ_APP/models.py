from django.db import models
from django.contrib.auth.models import User
import random
import string


class Deck(models.Model):
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
    ]

    title = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='decks')
    time_interval = models.CharField(max_length=20, default='10 secs')
    subject = models.CharField(max_length=100, default='Other')
    grade = models.CharField(max_length=20, default='N/A')
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='private')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.owner.username})"


class Card(models.Model):
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name='cards')
    front = models.TextField()
    back = models.TextField()
    choices = models.JSONField(default=list)

    def __str__(self):
        return f"Card {self.id} - {self.front[:30]}"


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


class Session(models.Model):
    deck = models.ForeignKey('Deck', on_delete=models.CASCADE, related_name='sessions')
    host = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_started = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = ''.join(random.choices(string.digits, k=6))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Session {self.code} for {self.deck.title}"


class Submission(models.Model):
    deck = models.ForeignKey('Deck', on_delete=models.CASCADE, related_name='submissions')
    session = models.ForeignKey('Session', on_delete=models.CASCADE, null=True, blank=True, related_name='submissions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    total = models.IntegerField(default=0)
    submission_time = models.DateTimeField(auto_now_add=True)

    def percentage(self):
        return round((self.score / self.total) * 100, 1) if self.total > 0 else 0

    def __str__(self):
        return f"{self.user.username} - {self.deck.title} ({self.score}/{self.total})"


class Participant(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    progress = models.IntegerField(default=0)
    total_cards = models.IntegerField(default=0)
