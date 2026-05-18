import json

from django.contrib.auth import login
from django.db.models import Avg, Count, ExpressionWrapper, F, FloatField
from django.http import Http404, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .forms import SignUpForm
from .language import get_prompt_text, get_quiz_ui_text, get_request_language, get_ui_text, normalize_language
from .models import Attempt, Quiz, UserPreference
from .storage import save_new_quiz, update_quiz


def _extract_quiz_json(raw: str) -> dict:
    # AI tools sometimes wrap the JSON in extra text, so we accept either
    # a clean object or a complete quiz-shaped JSON object inside the pasted
    # response. The decoder approach is safer than slicing from the first {
    # to the last }, because post-JSON instructions may contain braces too.
    raw = raw.strip()
    if not raw:
        raise ValueError("JSON is required")

    decoder = json.JSONDecoder()
    last_error = "Invalid JSON"

    for index, char in enumerate(raw):
        if char != "{":
            continue

        try:
            data, _ = decoder.raw_decode(raw[index:])
        except json.JSONDecodeError as exc:
            last_error = "Invalid JSON"
            continue

        if isinstance(data, dict) and "questions" in data:
            return _validate_quiz_json(data)

        try:
            return _validate_quiz_json(data)
        except ValueError as exc:
            last_error = str(exc)
            continue

    raise ValueError(last_error)


def _validate_quiz_json(data: object) -> dict:
    if not isinstance(data, dict):
        raise ValueError("JSON must be an object")

    if "questions" not in data or not isinstance(data["questions"], list):
        raise ValueError("Missing 'questions' array")
    if not data["questions"]:
        raise ValueError("The quiz must contain at least one question")

    if not isinstance(data.get("title"), str) or not data.get("title", "").strip():
        data["title"] = "Untitled quiz"

    for question_index, question in enumerate(data["questions"], start=1):
        if not isinstance(question, dict):
            raise ValueError(f"Question {question_index} must be an object")
        if not isinstance(question.get("question"), str) or not question["question"].strip():
            raise ValueError(f"Question {question_index} is missing question text")

        answers = question.get("answers")
        if not isinstance(answers, list) or len(answers) < 2:
            raise ValueError(f"Question {question_index} must have at least 2 answers")

        correct_count = 0
        for answer_index, answer in enumerate(answers, start=1):
            if not isinstance(answer, dict):
                raise ValueError(f"Question {question_index}, answer {answer_index} must be an object")
            if not isinstance(answer.get("text"), str) or not answer["text"].strip():
                raise ValueError(f"Question {question_index}, answer {answer_index} is missing answer text")
            if not isinstance(answer.get("correct"), bool):
                raise ValueError(f"Question {question_index}, answer {answer_index} must use true or false for correct")
            if answer["correct"]:
                correct_count += 1

        if correct_count == 0:
            raise ValueError(f"Question {question_index} must have at least 1 correct answer")

        sources = question.get("sources", [])
        if sources is not None and not isinstance(sources, list):
            raise ValueError(f"Question {question_index} sources must be an array")
        if isinstance(sources, list):
            for source_index, source in enumerate(sources, start=1):
                if not isinstance(source, dict):
                    raise ValueError(f"Question {question_index}, source {source_index} must be an object")

    return data


def _quiz_stats(quiz: Quiz) -> dict:
    # Keep stats formatting in one place so the list page and the attempt API
    # stay consistent.
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
    # Annotate the list view with aggregate stats up front to avoid per-row
    # queries while rendering.
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
    # The template only needs a simple flag to decide whether owner actions
    # should be shown on each row.
    quizzes = list(queryset)
    for quiz in quizzes:
        quiz.can_edit = _can_edit_quiz(request, quiz)
    return quizzes


def quizzes_list(request):
    ui = get_ui_text(get_request_language(request))
    quizzes = _quiz_cards_for_request(request, _quiz_list_queryset())
    return render(
        request,
        "quizforger/list.html",
        {
            "quizzes": quizzes,
            "page_title": ui["all_quizzes"],
            "active_list": "all",
        },
    )


@login_required
def my_quizzes(request):
    ui = get_ui_text(get_request_language(request))
    quizzes = _quiz_cards_for_request(request, _quiz_list_queryset().filter(owner=request.user))
    return render(
        request,
        "quizforger/list.html",
        {
            "quizzes": quizzes,
            "page_title": ui["my_quizzes"],
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
        UserPreference.objects.update_or_create(
            user=user,
            defaults={"language": get_request_language(request)},
        )
        login(request, user)
        return redirect("quizzes_list")

    return render(request, "registration/signup.html", {"form": form})


@ensure_csrf_cookie
def quiz_page(request, quiz_id):
    language = get_request_language(request)
    quiz = _get_quiz_or_404(quiz_id)
    return render(
        request,
        "quizforger/quiz.html",
        {
            "quiz": quiz,
            "quiz_ui": get_quiz_ui_text(language),
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

    raw_answered_count = payload.get("answered_count")
    if raw_answered_count in (None, ""):
        # Keep older cached frontend code working during development.
        answered_count = total
    else:
        try:
            answered_count = int(raw_answered_count)
        except (TypeError, ValueError):
            return HttpResponseBadRequest("answered_count must be an integer")

    if total <= 0:
        return HttpResponseBadRequest("Total must be greater than zero")
    if score < 0 or score > total:
        return HttpResponseBadRequest("Score must be between 0 and total")
    if answered_count < 0 or answered_count > total:
        return HttpResponseBadRequest("answered_count must be between 0 and total")

    if answered_count * 2 < total:
        # The quiz still returns feedback to the user, but it does not affect
        # public stats unless they answered at least half the questions.
        stats = _quiz_stats(quiz)
        stats["saved"] = False
        stats["message"] = "Attempt not counted because fewer than 50% of questions were answered."
        return JsonResponse(stats)

    user = request.user if request.user.is_authenticated else None
    Attempt.objects.create(quiz=quiz, user=user, score=score, total=total)

    stats = _quiz_stats(quiz)
    stats["saved"] = True
    stats["message"] = "Attempt saved."
    return JsonResponse(stats)


@require_http_methods(["GET", "POST"])
@login_required
def quiz_new(request):
    language = get_request_language(request)
    if request.method == "GET":
        return render(
            request,
            "quizforger/create.html",
            {
                "json_value": "",
                "prompt_text": get_prompt_text(language),
            },
        )

    raw = (request.POST.get("json") or "").strip()
    try:
        data = _extract_quiz_json(raw)
    except ValueError as exc:
        return HttpResponseBadRequest(str(exc))

    quiz = save_new_quiz(data, owner=request.user)
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
    try:
        data = _extract_quiz_json(raw)
    except ValueError as exc:
        return HttpResponseBadRequest(str(exc))

    quiz = update_quiz(quiz, data)
    return redirect("quiz_page", quiz_id=quiz.id)


@require_http_methods(["POST"])
@login_required
def quiz_delete(request, quiz_id):
    quiz = _get_quiz_or_404(quiz_id)
    if not _can_edit_quiz(request, quiz):
        return HttpResponseForbidden("You are not allowed to delete this quiz")

    quiz.delete()
    return redirect("my_quizzes")


@require_http_methods(["POST"])
def set_language(request):
    language = normalize_language(request.POST.get("language"))
    request.session["language"] = language

    if request.user.is_authenticated:
        UserPreference.objects.update_or_create(
            user=request.user,
            defaults={"language": language},
        )

    fallback = reverse("quizzes_list")
    next_url = request.POST.get("next") or fallback
    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = fallback

    return redirect(next_url)
