import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from quizforger.models import Attempt, Quiz
from quizforger.storage import save_new_quiz
from quizforger.tests.factories import quiz_document

User = get_user_model()


class QuizApiTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner@example.com",
            email="owner@example.com",
            password="Correct-Horse-42",
        )
        self.other = User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="Correct-Horse-43",
        )
        self.quiz = save_new_quiz(quiz_document(), owner=self.owner)

    def submission(self, *, submission_id=None, answers=None):
        return {
            "submission_id": str(submission_id or uuid.uuid4()),
            "answers": answers
            if answers is not None
            else [
                {"question_index": 0, "answer_indices": [0, 2]},
                {"question_index": 1, "answer_indices": [0]},
            ],
        }

    def test_public_quiz_api_does_not_expose_correct_answers(self):
        response = self.client.get(reverse("quiz_data", args=[self.quiz.id]))

        self.assertEqual(response.status_code, 200)
        question = response.json()["questions"][0]
        self.assertNotIn("correct", question["answers"][0])
        self.assertNotIn("explanation", question)

    def test_invalid_stored_quiz_returns_controlled_error(self):
        self.quiz.content = {"title": "Broken"}
        self.quiz.save(update_fields=["content"])

        response = self.client.get(reverse("quiz_data", args=[self.quiz.id]))

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"error": "Quiz data is invalid"})

    def test_attempt_score_is_calculated_on_server(self):
        payload = self.submission(answers=[{"question_index": 1, "answer_indices": [1]}])
        payload.update(score=999, total=999)

        response = self.client.post(
            reverse("quiz_attempt_create", args=[self.quiz.id]),
            payload,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["score"], 0)
        attempt = Attempt.objects.get()
        self.assertEqual((attempt.score, attempt.total), (0, 2))

    def test_incomplete_attempt_returns_feedback_but_is_not_saved(self):
        response = self.client.post(
            reverse("quiz_attempt_create", args=[self.quiz.id]),
            self.submission(answers=[]),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["saved"])
        self.assertEqual(Attempt.objects.count(), 0)

    def test_submission_id_makes_attempt_idempotent(self):
        submission_id = uuid.uuid4()
        url = reverse("quiz_attempt_create", args=[self.quiz.id])
        first = self.client.post(
            url, self.submission(submission_id=submission_id), content_type="application/json"
        )
        second = self.client.post(
            url, self.submission(submission_id=submission_id), content_type="application/json"
        )

        self.assertTrue(first.json()["saved"])
        self.assertFalse(second.json()["saved"])
        self.assertEqual(Attempt.objects.count(), 1)

    def test_invalid_submission_id_is_rejected(self):
        response = self.client.post(
            reverse("quiz_attempt_create", args=[self.quiz.id]),
            self.submission(submission_id="not-a-uuid"),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Attempt.objects.count(), 0)

    def test_invalid_json_attempt_is_rejected(self):
        response = self.client.post(
            reverse("quiz_attempt_create", args=[self.quiz.id]),
            data="{not-json",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Invalid JSON"})

    def test_non_owner_cannot_edit_or_archive_quiz(self):
        self.client.force_login(self.other)

        edit_response = self.client.get(reverse("quiz_edit", args=[self.quiz.id]))
        delete_response = self.client.post(reverse("quiz_delete", args=[self.quiz.id]))

        self.assertEqual(edit_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)
        self.quiz.refresh_from_db()
        self.assertIsNone(self.quiz.archived_at)

    def test_owner_archive_preserves_quiz_and_attempts(self):
        Attempt.objects.create(quiz=self.quiz, score=1, total=2)
        self.client.force_login(self.owner)

        response = self.client.post(reverse("quiz_delete", args=[self.quiz.id]))

        self.assertRedirects(response, reverse("my_quizzes"))
        self.quiz.refresh_from_db()
        self.assertIsNotNone(self.quiz.archived_at)
        self.assertEqual(Attempt.objects.filter(quiz=self.quiz).count(), 1)
        self.assertEqual(
            self.client.get(reverse("quiz_page", args=[self.quiz.id])).status_code, 404
        )

    def test_archived_quiz_is_hidden_from_lists(self):
        self.quiz.archived_at = self.quiz.updated_at
        self.quiz.save(update_fields=["archived_at"])

        response = self.client.get(reverse("quizzes_list"))

        self.assertNotContains(response, self.quiz.title)

    def test_public_list_does_not_expose_owner_email(self):
        response = self.client.get(reverse("quizzes_list"))

        self.assertContains(response, "QuizForger member")
        self.assertNotContains(response, self.owner.email)

    def test_healthcheck_verifies_database(self):
        response = self.client.get(reverse("healthz"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_healthcheck_returns_503_when_database_is_unavailable(self):
        with patch("quizforger.views.connection.cursor", side_effect=RuntimeError("offline")):
            response = self.client.get(reverse("healthz"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unhealthy"})

    def test_owner_can_edit_quiz(self):
        self.client.force_login(self.owner)
        updated = quiz_document()
        updated["title"] = "Updated title"

        get_response = self.client.get(reverse("quiz_edit", args=[self.quiz.id]))
        post_response = self.client.post(
            reverse("quiz_edit", args=[self.quiz.id]),
            {"json": __import__("json").dumps(updated)},
        )

        self.assertEqual(get_response.status_code, 200)
        self.assertRedirects(post_response, reverse("quiz_page", args=[self.quiz.id]))
        self.quiz.refresh_from_db()
        self.assertEqual(self.quiz.title, "Updated title")

    def test_language_redirect_rejects_external_target(self):
        response = self.client.post(
            reverse("set_language"),
            {"language": "de", "next": "https://attacker.example/steal"},
        )

        self.assertRedirects(response, reverse("quizzes_list"))
        self.assertEqual(self.client.session["language"], "de")


class QuizCreationTests(TestCase):
    def test_creation_requires_login(self):
        response = self.client.get(reverse("quiz_new"))

        self.assertRedirects(response, f"{reverse('login')}?next={reverse('quiz_new')}")

    def test_authenticated_user_can_create_valid_quiz(self):
        user = User.objects.create_user(username="creator@example.com", password="Correct-Horse-44")
        self.client.force_login(user)

        response = self.client.post(
            reverse("quiz_new"), {"json": __import__("json").dumps(quiz_document())}
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Quiz.objects.filter(owner=user).count(), 1)

    def test_signup_creates_preference_and_logs_user_in(self):
        response = self.client.post(
            reverse("signup"),
            {
                "email": "signup@example.com",
                "password1": "Correct-Horse-54",
                "password2": "Correct-Horse-54",
            },
        )

        self.assertRedirects(response, reverse("quizzes_list"))
        user = User.objects.get(email="signup@example.com")
        self.assertEqual(user.quizforger_preference.language, "en")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.id)
