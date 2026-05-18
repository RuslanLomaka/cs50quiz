from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.urls import path

from . import views
from .forms import EmailAuthenticationForm

urlpatterns = [
    path("", lambda request: redirect("quizzes_list"), name="home"),
    path("quizzes", views.quizzes_list, name="quizzes_list"),
    path("quizzes/mine", views.my_quizzes, name="my_quizzes"),
    path("quizzes/new", views.quiz_new, name="quiz_new"),
    path("quizzes/<str:quiz_id>/edit", views.quiz_edit, name="quiz_edit"),
    path("quizzes/<str:quiz_id>/delete", views.quiz_delete, name="quiz_delete"),
    path("quizzes/<str:quiz_id>", views.quiz_page, name="quiz_page"),
    path("api/quizzes/<str:quiz_id>", views.quiz_data, name="quiz_data"),
    path("api/quizzes/<str:quiz_id>/attempts", views.quiz_attempt_create, name="quiz_attempt_create"),
    path(
        "accounts/login",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=EmailAuthenticationForm,
        ),
        name="login",
    ),
    path("accounts/logout", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/signup", views.signup, name="signup"),
]
