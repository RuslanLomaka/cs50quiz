from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


UserModel = get_user_model()


class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        login_value = (username or kwargs.get(UserModel.EMAIL_FIELD) or "").strip()
        if not login_value or password is None:
            return None

        # First, honor normal Django username login exactly as entered.
        user = super().authenticate(request, username=login_value, password=password, **kwargs)
        if user is not None:
            return user

        # Then allow email login. Iterate safely in case older data contains
        # duplicate email addresses, which should not crash authentication.
        for user in UserModel.objects.filter(email__iexact=login_value).order_by("-is_superuser", "id"):
            if user.check_password(password) and self.user_can_authenticate(user):
                return user

        return None
