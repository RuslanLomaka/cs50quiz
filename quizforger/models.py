from django.conf import settings
from django.db import models
from django.db.models import F, Q


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
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "id"]
        indexes = [
            models.Index(fields=["archived_at", "-created_at"], name="quiz_active_created_idx"),
        ]

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
    submission_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "id"]
        constraints = [
            models.CheckConstraint(condition=Q(total__gt=0), name="attempt_total_positive"),
            models.CheckConstraint(
                condition=Q(score__lte=F("total")), name="attempt_score_lte_total"
            ),
            models.UniqueConstraint(
                fields=["quiz", "submission_id"],
                condition=Q(submission_id__isnull=False),
                name="attempt_unique_submission_per_quiz",
            ),
        ]

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
