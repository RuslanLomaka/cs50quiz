from django.test import SimpleTestCase

from quizforger.scoring import InvalidSubmission, public_quiz_payload, score_submission
from quizforger.tests.factories import quiz_document


class PublicQuizPayloadTests(SimpleTestCase):
    def test_answer_key_and_feedback_are_not_exposed(self):
        payload = public_quiz_payload(quiz_document())

        first_question = payload["questions"][0]
        self.assertTrue(first_question["multiple"])
        self.assertNotIn("explanation", first_question)
        self.assertNotIn("sources", first_question)
        self.assertNotIn("correct", first_question["answers"][0])


class ScoreSubmissionTests(SimpleTestCase):
    def test_server_scores_single_and_multiple_answers(self):
        payload = {
            "answers": [
                {"question_index": 0, "answer_indices": [0, 2]},
                {"question_index": 1, "answer_indices": [0]},
            ]
        }

        result = score_submission(quiz_document(), payload)

        self.assertEqual(result.score, 2)
        self.assertEqual(result.total, 2)
        self.assertEqual(result.answered_count, 2)
        self.assertEqual(result.feedback[0]["correct_answer_indices"], [0, 2])

    def test_partial_multiple_answer_is_wrong(self):
        result = score_submission(
            quiz_document(),
            {"answers": [{"question_index": 0, "answer_indices": [0]}]},
        )

        self.assertEqual(result.score, 0)
        self.assertEqual(result.feedback[0]["status"], "wrong")
        self.assertEqual(result.feedback[1]["status"], "missed")

    def test_rejects_duplicate_question_entry(self):
        payload = {
            "answers": [
                {"question_index": 0, "answer_indices": [0]},
                {"question_index": 0, "answer_indices": [2]},
            ]
        }

        with self.assertRaisesMessage(InvalidSubmission, "only be submitted once"):
            score_submission(quiz_document(), payload)

    def test_rejects_out_of_range_answer(self):
        payload = {"answers": [{"question_index": 1, "answer_indices": [99]}]}

        with self.assertRaisesMessage(InvalidSubmission, "out of range"):
            score_submission(quiz_document(), payload)
