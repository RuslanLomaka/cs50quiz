import json
from pathlib import Path

from django.db import migrations, models
from django.utils.dateparse import parse_datetime


def quizzes_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "quizzes"


def copy_quiz_files_to_db(apps, schema_editor):
    Quiz = apps.get_model("quizforger", "Quiz")
    qdir = quizzes_dir()
    if not qdir.exists():
        return

    for path in qdir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        created_at = parse_datetime(data.get("created_at") or "")
        updated_at = parse_datetime(data.get("updated_at") or "")
        quiz, _ = Quiz.objects.get_or_create(
            pk=path.stem,
            defaults={
                "title": (data.get("title") or "").strip() or "Untitled quiz",
                "json_filename": path.name,
                "created_at": created_at or parse_datetime("2000-01-01T00:00:00Z"),
                "updated_at": updated_at or created_at or parse_datetime("2000-01-01T00:00:00Z"),
            },
        )

        quiz.title = (data.get("title") or "").strip() or "Untitled quiz"
        quiz.content = data
        if created_at is not None:
            quiz.created_at = created_at
        if updated_at is not None:
            quiz.updated_at = updated_at
        quiz.save(update_fields=["title", "content", "created_at", "updated_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("quizforger", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="quiz",
            name="content",
            field=models.JSONField(default=dict),
        ),
        migrations.RunPython(copy_quiz_files_to_db, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="quiz",
            name="json_filename",
        ),
    ]
