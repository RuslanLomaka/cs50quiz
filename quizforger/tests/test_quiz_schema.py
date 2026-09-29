import json

from django.test import SimpleTestCase

from quizforger.quiz_schema import MAX_QUESTIONS, extract_quiz_json, validate_quiz_json
from quizforger.tests.factories import quiz_document


class QuizJsonExtractionTests(SimpleTestCase):
    def test_extracts_json_before_trailing_instruction(self):
        raw = json.dumps(quiz_document()) + "\nCopy the JSON above back into QuizForger."

        data = extract_quiz_json(raw)

        self.assertEqual(data["title"], "Safe quiz")
        self.assertEqual(len(data["questions"]), 2)

    def test_skips_non_quiz_object_before_real_quiz(self):
        raw = 'Example: {"not": "the quiz"}\n' + json.dumps(quiz_document())

        self.assertEqual(extract_quiz_json(raw)["title"], "Safe quiz")

    def test_rejects_answer_without_boolean_correct_value(self):
        data = quiz_document()
        data["questions"][0]["answers"][0]["correct"] = "true"

        with self.assertRaisesMessage(ValueError, "must use true or false"):
            validate_quiz_json(data)

    def test_returns_trimmed_canonical_document(self):
        data = quiz_document()
        data["unknown"] = {"large": "ignored"}
        data["title"] = "  Title  "
        data["questions"][0]["question"] = "  Question?  "

        cleaned = validate_quiz_json(data)

        self.assertEqual(cleaned["title"], "Title")
        self.assertEqual(cleaned["questions"][0]["question"], "Question?")
        self.assertNotIn("unknown", cleaned)

    def test_rejects_too_many_questions(self):
        question = quiz_document()["questions"][1]
        data = {"title": "Large", "questions": [question] * (MAX_QUESTIONS + 1)}

        with self.assertRaisesMessage(ValueError, "at most"):
            validate_quiz_json(data)

    def test_rejects_unsafe_source_scheme(self):
        data = quiz_document()
        data["questions"][0]["sources"][0]["url"] = "javascript:alert(1)"

        with self.assertRaisesMessage(ValueError, "valid http or https URL"):
            validate_quiz_json(data)

    def test_rejects_source_url_credentials(self):
        data = quiz_document()
        data["questions"][0]["sources"][0]["url"] = "https://user:pass@example.com"

        with self.assertRaisesMessage(ValueError, "must not contain credentials"):
            validate_quiz_json(data)
