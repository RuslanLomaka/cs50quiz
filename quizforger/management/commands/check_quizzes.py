from django.core.management.base import BaseCommand, CommandError

from quizforger.models import Quiz
from quizforger.quiz_schema import validate_quiz_json


class Command(BaseCommand):
    help = "Validate every stored quiz against the current persisted schema."

    def handle(self, *args, **options):
        invalid_ids = []
        checked = 0
        for quiz in Quiz.objects.only("id", "content").iterator():
            checked += 1
            try:
                validate_quiz_json(quiz.content)
            except ValueError:
                invalid_ids.append(quiz.id)

        if invalid_ids:
            sample = ", ".join(invalid_ids[:20])
            suffix = "" if len(invalid_ids) <= 20 else ", ..."
            raise CommandError(f"Found {len(invalid_ids)} invalid stored quizzes: {sample}{suffix}")
        self.stdout.write(self.style.SUCCESS(f"Stored quizzes valid: {checked}"))
