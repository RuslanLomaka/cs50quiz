from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from quizforger.context_processors import IMPRINT_URL
from quizforger.language import UI_TEXT

User = get_user_model()


class LegalPagesTests(TestCase):
    def test_privacy_page_is_public(self):
        response = self.client.get(reverse("privacy"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Datenschutzerklärung")
        self.assertContains(response, f'href="{IMPRINT_URL}"')

    def test_privacy_page_only_answers_get(self):
        response = self.client.post(reverse("privacy"))

        self.assertEqual(response.status_code, 405)

    def test_every_page_links_to_imprint_and_privacy(self):
        for name in ("quizzes_list", "login", "signup", "privacy"):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))

                self.assertContains(response, f'<a href="{IMPRINT_URL}">')
                self.assertContains(response, f'<a href="{reverse("privacy")}">')

    def test_footer_labels_follow_the_chosen_language(self):
        self.client.post(reverse("set_language"), {"language": "de"})

        response = self.client.get(reverse("quizzes_list"))

        self.assertContains(response, ">Impressum</a>")
        self.assertContains(response, ">Datenschutz</a>")

    def test_signup_page_points_to_privacy_policy_where_the_email_is_collected(self):
        response = self.client.get(reverse("signup"))

        self.assertContains(response, UI_TEXT["en"]["signup_privacy"])

    def test_all_languages_define_the_same_ui_keys(self):
        english = set(UI_TEXT["en"])
        for language, texts in UI_TEXT.items():
            with self.subTest(language=language):
                self.assertEqual(set(texts), english)
