from django.test import TestCase

from quizforger.storage import save_new_quiz
from quizforger.tests.factories import quiz_document


class QuizStorageTests(TestCase):
    def test_quiz_ids_do_not_collide_within_the_same_second(self):
        first = save_new_quiz(quiz_document())
        second = save_new_quiz(quiz_document())

        self.assertNotEqual(first.id, second.id)
        self.assertLessEqual(len(first.id), 32)
