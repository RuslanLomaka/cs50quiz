from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class HardeningMigrationTests(TransactionTestCase):
    migrate_from = [("quizforger", "0003_userpreference")]
    migrate_to = [("quizforger", "0005_normalize_legacy_quiz_sources")]

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        old_apps = executor.loader.project_state(self.migrate_from).apps
        Quiz = old_apps.get_model("quizforger", "Quiz")
        Attempt = old_apps.get_model("quizforger", "Attempt")

        now = timezone.now()
        Quiz.objects.create(
            id="legacy-quiz",
            title="Legacy quiz",
            created_at=now,
            updated_at=now,
            content={
                "title": "Legacy quiz",
                "questions": [
                    {
                        "id": 1,
                        "question": "Question?",
                        "answers": [
                            {"text": "Yes", "correct": True},
                            {"text": "No", "correct": False},
                        ],
                        "explanation": "Explanation",
                        "sources": [
                            {
                                "title": "Docs",
                                "url": "[Official docs](https://example.com/docs)",
                                "note": "Read this",
                            },
                            {"title": "Unsafe", "url": "javascript:alert(1)"},
                        ],
                    }
                ],
            },
        )
        Attempt.objects.create(quiz_id="legacy-quiz", score=5, total=0)
        Attempt.objects.create(quiz_id="legacy-quiz", score=8, total=3)

        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        self.apps = executor.loader.project_state(self.migrate_to).apps

    def tearDown(self):
        MigrationExecutor(connection).migrate(self.migrate_to)
        super().tearDown()

    def test_invalid_attempts_are_removed_or_clamped_before_constraints(self):
        Attempt = self.apps.get_model("quizforger", "Attempt")

        attempts = list(Attempt.objects.order_by("id"))

        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0].score, 3)
        self.assertEqual(attempts[0].total, 3)

    def test_legacy_markdown_sources_are_normalized_and_unsafe_sources_removed(self):
        Quiz = self.apps.get_model("quizforger", "Quiz")

        sources = Quiz.objects.get(pk="legacy-quiz").content["questions"][0]["sources"]

        self.assertEqual(
            sources,
            [
                {
                    "title": "Docs",
                    "url": "https://example.com/docs",
                    "note": "Read this",
                }
            ],
        )
