from django.contrib import admin

from .models import Attempt, Quiz


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "owner", "created_at", "updated_at")
    search_fields = ("id", "title", "owner__username", "owner__email")
    list_filter = ("created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "quiz", "user", "score", "total", "created_at")
    search_fields = ("quiz__title", "quiz__id", "user__username", "user__email")
    list_filter = ("created_at",)
    ordering = ("-created_at",)
