import json

from django.contrib.auth import login
from django.db.models import Avg, Count, ExpressionWrapper, F, FloatField
from django.http import Http404, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .forms import SignUpForm
from .models import Attempt, Quiz
from .storage import list_quizzes, save_new_quiz, update_quiz


def _quiz_stats(quiz: Quiz) -> dict:
    stats = quiz.attempts.aggregate(
        attempt_count=Count("id"),
        average_percent=Avg(
            ExpressionWrapper(F("score") * 100.0 / F("total"), output_field=FloatField())
        ),
    )
    attempt_count = stats["attempt_count"] or 0
    average_percent = stats["average_percent"]
    average_percent = 0.0 if average_percent is None else round(average_percent, 1)
    return {
        "attempt_count": attempt_count,
        "average_percent": average_percent,
    }


def _quiz_list_queryset():
    return Quiz.objects.select_related("owner").annotate(
        attempt_count=Count("attempts"),
        average_percent=Avg(
            ExpressionWrapper(F("attempts__score") * 100.0 / F("attempts__total"), output_field=FloatField())
        ),
    )


def _get_quiz_or_404(quiz_id: str) -> Quiz:
    try:
        return Quiz.objects.get(id=quiz_id)
    except Quiz.DoesNotExist:
        raise Http404("Quiz not found")


def _can_edit_quiz(request, quiz: Quiz) -> bool:
    return request.user.is_authenticated and (
        request.user.is_staff or quiz.owner_id == request.user.id
    )


def _quiz_cards_for_request(request, queryset):
    quizzes = list(queryset)
    for quiz in quizzes:
        quiz.can_edit = _can_edit_quiz(request, quiz)
    return quizzes


def quizzes_list(request):
    quizzes = _quiz_cards_for_request(request, _quiz_list_queryset())
    return render(
        request,
        "quizforger/list.html",
        {
            "quizzes": quizzes,
            "page_title": "All quizzes",
            "active_list": "all",
        },
    )


@login_required
def my_quizzes(request):
    quizzes = _quiz_cards_for_request(request, _quiz_list_queryset().filter(owner=request.user))
    return render(
        request,
        "quizforger/list.html",
        {
            "quizzes": quizzes,
            "page_title": "My quizzes",
            "active_list": "mine",
        },
    )


@require_http_methods(["GET", "POST"])
def signup(request):
    if request.user.is_authenticated:
        return redirect("quizzes_list")

    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("quizzes_list")

    return render(request, "registration/signup.html", {"form": form})


@ensure_csrf_cookie
def quiz_page(request, quiz_id):
    quiz = _get_quiz_or_404(quiz_id)
    return render(
        request,
        "quizforger/quiz.html",
        {
            "quiz": quiz,
        },
    )


def quiz_data(request, quiz_id):
    quiz = _get_quiz_or_404(quiz_id)
    return JsonResponse(quiz.content, safe=False)


@require_http_methods(["POST"])
def quiz_attempt_create(request, quiz_id):
    quiz = _get_quiz_or_404(quiz_id)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    try:
        score = int(payload.get("score"))
        total = int(payload.get("total"))
    except (TypeError, ValueError):
        return HttpResponseBadRequest("Score and total must be integers")

    if total <= 0:
        return HttpResponseBadRequest("Total must be greater than zero")
    if score < 0 or score > total:
        return HttpResponseBadRequest("Score must be between 0 and total")

    user = request.user if request.user.is_authenticated else None
    Attempt.objects.create(quiz=quiz, user=user, score=score, total=total)

    stats = _quiz_stats(quiz)
    return JsonResponse(stats)


@require_http_methods(["GET", "POST"])
@login_required
def quiz_new(request):
    if request.method == "GET":
        return render(
            request,
            "quizforger/create.html",
            {
                "json_value": "",
            },
        )

    raw = (request.POST.get("json") or "").strip()
    if not raw:
        return HttpResponseBadRequest("JSON is required")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    if not isinstance(data, dict):
        return HttpResponseBadRequest("JSON must be an object")
    if "questions" not in data or not isinstance(data["questions"], list):
        return HttpResponseBadRequest("Missing 'questions' array")

    if not isinstance(data.get("title"), str) or not data.get("title", "").strip():
        data["title"] = "Untitled quiz"

    owner = request.user if request.user.is_authenticated else None
    quiz = save_new_quiz(data, owner=owner)
    return redirect("quiz_page", quiz_id=quiz.id)


@require_http_methods(["GET", "POST"])
@login_required
def quiz_edit(request, quiz_id):
    quiz = _get_quiz_or_404(quiz_id)
    if not _can_edit_quiz(request, quiz):
        return HttpResponseForbidden("You are not allowed to edit this quiz")

    if request.method == "GET":
        return render(
            request,
            "quizforger/editor.html",
            {
                "mode": "edit",
                "quiz": quiz,
                "json_value": json.dumps(quiz.content, ensure_ascii=False, indent=2),
            },
        )

    raw = (request.POST.get("json") or "").strip()
    if not raw:
        return HttpResponseBadRequest("JSON is required")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    if not isinstance(data, dict):
        return HttpResponseBadRequest("JSON must be an object")
    if "questions" not in data or not isinstance(data["questions"], list):
        return HttpResponseBadRequest("Missing 'questions' array")

    if not isinstance(data.get("title"), str) or not data.get("title", "").strip():
        data["title"] = "Untitled quiz"

    quiz = update_quiz(quiz, data)
    return redirect("quiz_page", quiz_id=quiz.id)
