from django.conf import settings
from django.db import models


class Quiz(models.Model):
    id = models.CharField(primary_key=True, max_length=32)
    title = models.CharField(max_length=255)
    content = models.JSONField(default=dict)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_quizzes",
    )
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at", "id"]

    def __str__(self) -> str:
        return self.title


class Attempt(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="quiz_attempts",
    )
    score = models.PositiveIntegerField()
    total = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "id"]

    def __str__(self) -> str:
        return f"{self.quiz_id}: {self.score}/{self.total}"


class UserPreference(models.Model):
    LANGUAGE_CHOICES = [
        ("en", "English"),
        ("de", "Deutsch"),
        ("uk", "Українська"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quizforger_preference",
    )
    language = models.CharField(max_length=8, choices=LANGUAGE_CHOICES, default="en")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user}: {self.language}"
