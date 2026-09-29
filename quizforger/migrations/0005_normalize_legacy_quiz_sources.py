import re
from urllib.parse import urlsplit

from django.db import migrations

MARKDOWN_URL = re.compile(r"^\s*\[[^\]]*\]\((https?://[^)\s]+)\)\s*$", re.IGNORECASE)
MAX_SOURCES = 5


def _clean_text(value, max_length):
    return value.strip()[:max_length] if isinstance(value, str) else ""


def _clean_url(value):
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    markdown_match = MARKDOWN_URL.fullmatch(candidate)
    if markdown_match:
        candidate = markdown_match.group(1)
    if len(candidate) > 2048 or any(ord(character) < 32 for character in candidate):
        return None
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return None
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        return None
    return candidate


def normalize_legacy_quiz_sources(apps, schema_editor):
    Quiz = apps.get_model("quizforger", "Quiz")
    for quiz in Quiz.objects.iterator():
        content = quiz.content
        if not isinstance(content, dict) or not isinstance(content.get("questions"), list):
            continue

        changed = False
        for question in content["questions"]:
            if not isinstance(question, dict):
                continue
            raw_sources = question.get("sources", [])
            if not isinstance(raw_sources, list):
                question["sources"] = []
                changed = True
                continue

            cleaned_sources = []
            for source in raw_sources:
                if not isinstance(source, dict):
                    changed = True
                    continue
                url = _clean_url(source.get("url"))
                if not url:
                    changed = True
                    continue
                cleaned_source = {
                    "title": _clean_text(source.get("title"), 255),
                    "url": url,
                    "note": _clean_text(source.get("note"), 1000),
                }
                cleaned_sources.append(cleaned_source)
                changed = changed or cleaned_source != source
                if len(cleaned_sources) == MAX_SOURCES:
                    changed = changed or len(raw_sources) > MAX_SOURCES
                    break

            if cleaned_sources != raw_sources:
                question["sources"] = cleaned_sources
                changed = True

        if changed:
            quiz.content = content
            quiz.save(update_fields=["content"])


class Migration(migrations.Migration):
    dependencies = [
        ("quizforger", "0004_harden_quiz_and_attempt_data"),
    ]

    operations = [
        migrations.RunPython(normalize_legacy_quiz_sources, migrations.RunPython.noop),
    ]
