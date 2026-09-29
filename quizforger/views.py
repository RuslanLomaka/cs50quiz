import json
import logging
import uuid

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import connection, transaction
from django.db.models import Avg, Count, ExpressionWrapper, F, FloatField
from django.http import Http404, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods

from .forms import SignUpForm
from .language import (
    get_prompt_text,
    get_quiz_ui_text,
    get_request_language,
    get_ui_text,
    normalize_language,
)
from .models import Attempt, Quiz, UserPreference
from .quiz_schema import extract_quiz_json as _extract_quiz_json
from .scoring import InvalidSubmission, public_quiz_payload, score_submission
from .storage import archive_quiz, save_new_quiz, update_quiz

logger = logging.getLogger(__name__)


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
    return (
        Quiz.objects.filter(archived_at__isnull=True)
        .select_related("owner")
        .annotate(
            attempt_count=Count("attempts"),
            average_percent=Avg(
                ExpressionWrapper(
                    F("attempts__score") * 100.0 / F("attempts__total"), output_field=FloatField()
                )
            ),
        )
    )


def _get_quiz_or_404(quiz_id: str) -> Quiz:
    try:
        return Quiz.objects.get(id=quiz_id, archived_at__isnull=True)
    except Quiz.DoesNotExist as exc:
        raise Http404("Quiz not found") from exc


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


@require_GET
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


@require_GET
def quiz_data(request, quiz_id):
    quiz = _get_quiz_or_404(quiz_id)
    try:
        payload = public_quiz_payload(quiz.content)
    except ValueError:
        logger.exception(
            "stored_quiz_invalid",
            extra={"event": "stored_quiz_invalid", "quiz_id": quiz.id},
        )
        return JsonResponse({"error": "Quiz data is invalid"}, status=500)
    return JsonResponse(payload)


@require_http_methods(["POST"])
def quiz_attempt_create(request, quiz_id):
    quiz = _get_quiz_or_404(quiz_id)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    try:
        result = score_submission(quiz.content, payload)
    except (InvalidSubmission, ValueError) as exc:
        logger.warning(
            "attempt_rejected",
            extra={"event": "attempt_rejected", "quiz_id": quiz.id, "reason": str(exc)},
        )
        return JsonResponse({"error": str(exc)}, status=400)

    response = {
        "score": result.score,
        "total": result.total,
        "answered_count": result.answered_count,
        "feedback": result.feedback,
    }
    if result.answered_count * 2 < result.total:
        response.update(_quiz_stats(quiz))
        response.update(
            saved=False,
            message="Attempt not counted because fewer than 50% of questions were answered.",
        )
        logger.info(
            "attempt_not_counted",
            extra={
                "event": "attempt_not_counted",
                "quiz_id": quiz.id,
                "answered_count": result.answered_count,
                "total": result.total,
            },
        )
        return JsonResponse(response)

    try:
        submission_id = uuid.UUID(str(payload.get("submission_id")))
    except (TypeError, ValueError, AttributeError):
        return JsonResponse({"error": "submission_id must be a valid UUID"}, status=400)

    user = request.user if request.user.is_authenticated else None
    with transaction.atomic():
        _, created = Attempt.objects.get_or_create(
            quiz=quiz,
            submission_id=submission_id,
            defaults={
                "user": user,
                "score": result.score,
                "total": result.total,
            },
        )

    response.update(_quiz_stats(quiz))
    response["saved"] = created
    response["message"] = "Attempt saved." if created else "This attempt was already recorded."
    logger.info(
        "attempt_recorded" if created else "attempt_duplicate",
        extra={
            "event": "attempt_recorded" if created else "attempt_duplicate",
            "quiz_id": quiz.id,
            "user_id": getattr(user, "id", None),
            "score": result.score,
            "total": result.total,
        },
    )
    return JsonResponse(response)


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
        logger.warning(
            "quiz_import_rejected",
            extra={"event": "quiz_import_rejected", "user_id": request.user.id, "reason": str(exc)},
        )
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
        logger.warning(
            "quiz_update_rejected",
            extra={
                "event": "quiz_update_rejected",
                "quiz_id": quiz.id,
                "user_id": request.user.id,
                "reason": str(exc),
            },
        )
        return HttpResponseBadRequest(str(exc))

    quiz = update_quiz(quiz, data)
    return redirect("quiz_page", quiz_id=quiz.id)


@require_http_methods(["POST"])
@login_required
def quiz_delete(request, quiz_id):
    quiz = _get_quiz_or_404(quiz_id)
    if not _can_edit_quiz(request, quiz):
        return HttpResponseForbidden("You are not allowed to delete this quiz")

    archive_quiz(quiz, actor_id=request.user.id)
    return redirect("my_quizzes")


@require_GET
def healthz(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        logger.exception("healthcheck_failed", extra={"event": "healthcheck_failed"})
        return JsonResponse({"status": "unhealthy"}, status=503)
    return JsonResponse({"status": "ok"})


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
