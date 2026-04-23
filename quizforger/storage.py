from datetime import datetime, timezone

from .models import Quiz


def list_quizzes() -> list[Quiz]:
    return list(Quiz.objects.all())


def _generate_quiz_id() -> str:
    return datetime.now(timezone.utc).strftime("q_%Y%m%d_%H%M%S")


def save_new_quiz(data: dict, owner=None) -> Quiz:
    quiz_id = _generate_quiz_id()
    now = datetime.now(timezone.utc)
    timestamp = now.isoformat().replace("+00:00", "Z")

    stored_data = dict(data)
    stored_data.setdefault("id", quiz_id)
    stored_data.setdefault("version", 1)
    stored_data.setdefault("created_at", timestamp)
    stored_data["updated_at"] = timestamp

    return Quiz.objects.create(
        id=quiz_id,
        title=(stored_data.get("title") or "").strip() or "Untitled quiz",
        content=stored_data,
        owner=owner,
        created_at=now,
        updated_at=now,
    )


def update_quiz(quiz: Quiz, data: dict) -> Quiz:
    now = datetime.now(timezone.utc)
    timestamp = now.isoformat().replace("+00:00", "Z")

    stored_data = dict(data)
    stored_data["id"] = quiz.id
    stored_data.setdefault("version", quiz.content.get("version", 1) if isinstance(quiz.content, dict) else 1)
    stored_data.setdefault(
        "created_at",
        quiz.content.get("created_at") if isinstance(quiz.content, dict) else quiz.created_at.isoformat().replace("+00:00", "Z"),
    )
    stored_data["updated_at"] = timestamp

    quiz.title = (stored_data.get("title") or "").strip() or "Untitled quiz"
    quiz.content = stored_data
    quiz.updated_at = now
    quiz.save(update_fields=["title", "content", "updated_at"])
    return quiz
