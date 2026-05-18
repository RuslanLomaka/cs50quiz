from django.test import SimpleTestCase

from .language import get_quiz_ui_text
from .views import _extract_quiz_json


class LanguageCatalogTests(SimpleTestCase):
    def test_quiz_player_translations_are_available(self):
        self.assertEqual(get_quiz_ui_text("en")["score"], "Score")
        self.assertEqual(get_quiz_ui_text("de")["score"], "Punktzahl")
        self.assertEqual(get_quiz_ui_text("uk")["score"], "Результат")


class QuizJsonExtractionTests(SimpleTestCase):
    def test_extracts_json_before_trailing_instruction(self):
        raw = """
        {
          "title": "Sample",
          "questions": [
            {
              "id": 1,
              "question": "Two plus two?",
              "answers": [
                { "text": "4", "correct": true },
                { "text": "5", "correct": false }
              ]
            }
          ]
        }

        Now copy the JSON above, go back to QuizForger, and paste it there.
        """

        data = _extract_quiz_json(raw)

        self.assertEqual(data["title"], "Sample")
        self.assertEqual(len(data["questions"]), 1)

    def test_skips_non_quiz_object_before_real_quiz(self):
        raw = """
        Here is a tiny example first: {"not": "the quiz"}

        {
          "title": "Real quiz",
          "questions": [
            {
              "id": 1,
              "question": "Ready?",
              "answers": [
                { "text": "Yes", "correct": true },
                { "text": "No", "correct": false }
              ]
            }
          ]
        }
        """

        data = _extract_quiz_json(raw)

        self.assertEqual(data["title"], "Real quiz")

    def test_rejects_answer_without_boolean_correct_value(self):
        raw = """
        {
          "title": "Bad quiz",
          "questions": [
            {
              "id": 1,
              "question": "Ready?",
              "answers": [
                { "text": "Yes", "correct": "true" },
                { "text": "No", "correct": false }
              ]
            }
          ]
        }
        """

        with self.assertRaisesMessage(ValueError, "must use true or false"):
            _extract_quiz_json(raw)
