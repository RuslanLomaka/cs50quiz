import logging
import uuid

from django.utils import timezone

from .models import Quiz

logger = logging.getLogger(__name__)


def _generate_quiz_id() -> str:
    return f"q_{uuid.uuid4().hex[:30]}"


def save_new_quiz(data: dict, owner=None) -> Quiz:
    # Store a few metadata fields inside the JSON itself so the quiz stays
    # self-describing even if it is exported later.
    quiz_id = _generate_quiz_id()
    now = timezone.now()
    timestamp = now.isoformat().replace("+00:00", "Z")

    stored_data = dict(data)
    stored_data.setdefault("id", quiz_id)
    stored_data.setdefault("created_at", timestamp)
    stored_data["updated_at"] = timestamp

    quiz = Quiz.objects.create(
        id=quiz_id,
        title=(stored_data.get("title") or "").strip() or "Untitled quiz",
        content=stored_data,
        owner=owner,
        created_at=now,
        updated_at=now,
    )
    logger.info(
        "quiz_created",
        extra={"event": "quiz_created", "quiz_id": quiz.id, "owner_id": quiz.owner_id},
    )
    return quiz


def update_quiz(quiz: Quiz, data: dict) -> Quiz:
    # Updating keeps the same quiz identity and original creation metadata,
    # while refreshing the JSON content and updated timestamp.
    now = timezone.now()
    timestamp = now.isoformat().replace("+00:00", "Z")

    stored_data = dict(data)
    stored_data["id"] = quiz.id
    stored_data.setdefault(
        "created_at",
        quiz.content.get("created_at")
        if isinstance(quiz.content, dict)
        else quiz.created_at.isoformat().replace("+00:00", "Z"),
    )
    stored_data["updated_at"] = timestamp

    quiz.title = (stored_data.get("title") or "").strip() or "Untitled quiz"
    quiz.content = stored_data
    quiz.updated_at = now
    quiz.save(update_fields=["title", "content", "updated_at"])
    logger.info(
        "quiz_updated",
        extra={"event": "quiz_updated", "quiz_id": quiz.id, "owner_id": quiz.owner_id},
    )
    return quiz


def archive_quiz(quiz: Quiz, *, actor_id: int | None) -> Quiz:
    quiz.archived_at = timezone.now()
    quiz.save(update_fields=["archived_at"])
    logger.info(
        "quiz_archived",
        extra={"event": "quiz_archived", "quiz_id": quiz.id, "actor_id": actor_id},
    )
    return quiz
