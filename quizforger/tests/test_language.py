from django.test import SimpleTestCase

from quizforger.language import get_quiz_ui_text


class LanguageCatalogTests(SimpleTestCase):
    def test_quiz_player_translations_are_available(self):
        self.assertEqual(get_quiz_ui_text("en")["score"], "Score")
        self.assertEqual(get_quiz_ui_text("de")["score"], "Punktzahl")
        self.assertEqual(get_quiz_ui_text("uk")["score"], "Результат")
