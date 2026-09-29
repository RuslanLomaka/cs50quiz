from django.contrib.auth import get_user_model
from django.test import TestCase

from quizforger.auth_backends import EmailOrUsernameModelBackend
from quizforger.forms import SignUpForm

User = get_user_model()


class AuthenticationBackendTests(TestCase):
    def setUp(self):
        self.backend = EmailOrUsernameModelBackend()
        self.user = User.objects.create_user(
            username="author",
            email="Author@Example.com",
            password="Correct-Horse-51",
        )

    def test_authenticates_by_username(self):
        authenticated = self.backend.authenticate(
            request=None,
            username="author",
            password="Correct-Horse-51",
        )

        self.assertEqual(authenticated, self.user)

    def test_authenticates_by_email_case_insensitively(self):
        authenticated = self.backend.authenticate(
            request=None,
            username="author@example.COM",
            password="Correct-Horse-51",
        )

        self.assertEqual(authenticated, self.user)

    def test_rejects_missing_or_wrong_credentials(self):
        self.assertIsNone(self.backend.authenticate(request=None, username="", password="x"))
        self.assertIsNone(
            self.backend.authenticate(request=None, username="author", password="wrong-password")
        )

    def test_duplicate_legacy_email_does_not_crash(self):
        matching = User.objects.create_user(
            username="second-author",
            email="author@example.com",
            password="Correct-Horse-52",
        )

        authenticated = self.backend.authenticate(
            request=None,
            username="author@example.com",
            password="Correct-Horse-52",
        )

        self.assertEqual(authenticated, matching)


class SignUpFormTests(TestCase):
    def valid_data(self, **overrides):
        data = {
            "email": "new@example.com",
            "password1": "Correct-Horse-53",
            "password2": "Correct-Horse-53",
        }
        data.update(overrides)
        return data

    def test_saves_normalized_email_as_username(self):
        form = SignUpForm(data=self.valid_data(email="  New@Example.COM "))

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.email, "new@example.com")
        self.assertEqual(user.username, "new@example.com")
        self.assertTrue(user.check_password("Correct-Horse-53"))

    def test_rejects_duplicate_email_case_insensitively(self):
        User.objects.create_user(username="existing", email="new@example.com")
        form = SignUpForm(data=self.valid_data(email="NEW@example.com"))

        self.assertFalse(form.is_valid())
        self.assertIn("already exists", form.errors["email"][0])

    def test_rejects_password_mismatch(self):
        form = SignUpForm(data=self.valid_data(password2="Different-Horse-53"))

        self.assertFalse(form.is_valid())
        self.assertIn("did not match", form.errors["password2"][0])

    def test_rejects_common_password(self):
        form = SignUpForm(data=self.valid_data(password1="password", password2="password"))

        self.assertFalse(form.is_valid())
        self.assertIn("too common", " ".join(form.errors["password1"]).lower())
