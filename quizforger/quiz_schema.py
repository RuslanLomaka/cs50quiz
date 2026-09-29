import json
from urllib.parse import urlsplit

MAX_IMPORT_BYTES = 512_000
MAX_QUESTIONS = 100
MAX_ANSWERS_PER_QUESTION = 12
MAX_SOURCES_PER_QUESTION = 5
MAX_TITLE_LENGTH = 255
MAX_QUESTION_LENGTH = 2_000
MAX_ANSWER_LENGTH = 1_000
MAX_EXPLANATION_LENGTH = 5_000
MAX_SOURCE_TITLE_LENGTH = 255
MAX_SOURCE_NOTE_LENGTH = 1_000
MAX_SOURCE_URL_LENGTH = 2_048


def _required_text(value, *, label: str, max_length: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")
    cleaned = value.strip()
    if len(cleaned) > max_length:
        raise ValueError(f"{label} must be at most {max_length} characters")
    return cleaned


def _optional_text(value, *, label: str, max_length: int) -> str:
    if value in (None, ""):
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text")
    cleaned = value.strip()
    if len(cleaned) > max_length:
        raise ValueError(f"{label} must be at most {max_length} characters")
    return cleaned


def _source_url(value, *, label: str) -> str:
    url = _required_text(value, label=label, max_length=MAX_SOURCE_URL_LENGTH)
    if any(ord(char) < 32 for char in url):
        raise ValueError(f"{label} contains invalid characters")
    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"{label} must be a valid http or https URL")
    if parsed.username or parsed.password:
        raise ValueError(f"{label} must not contain credentials")
    return url


def extract_quiz_json(raw: str) -> dict:
    """Extract and validate the first quiz-shaped JSON object from pasted text."""

    if not isinstance(raw, str):
        raise ValueError("JSON is required")
    if len(raw.encode("utf-8")) > MAX_IMPORT_BYTES:
        raise ValueError(f"Quiz JSON must be smaller than {MAX_IMPORT_BYTES // 1_000} KB")
    raw = raw.strip()
    if not raw:
        raise ValueError("JSON is required")

    decoder = json.JSONDecoder()
    last_error = "Invalid JSON"
    candidate_count = 0
    for index, char in enumerate(raw):
        if char != "{":
            continue
        candidate_count += 1
        if candidate_count > 100:
            break
        try:
            data, _ = decoder.raw_decode(raw[index:])
        except json.JSONDecodeError:
            continue
        try:
            return validate_quiz_json(data)
        except ValueError as exc:
            last_error = str(exc)
    raise ValueError(last_error)


def validate_quiz_json(data: object) -> dict:
    """Return a bounded canonical quiz document suitable for persistence."""

    if not isinstance(data, dict):
        raise ValueError("JSON must be an object")

    title_value = data.get("title")
    title = (
        "Untitled quiz"
        if title_value in (None, "")
        else _required_text(
            title_value,
            label="Quiz title",
            max_length=MAX_TITLE_LENGTH,
        )
    )

    questions = data.get("questions")
    if not isinstance(questions, list):
        raise ValueError("Missing 'questions' array")
    if not questions:
        raise ValueError("The quiz must contain at least one question")
    if len(questions) > MAX_QUESTIONS:
        raise ValueError(f"The quiz may contain at most {MAX_QUESTIONS} questions")

    cleaned_questions = []
    for question_index, question in enumerate(questions, start=1):
        if not isinstance(question, dict):
            raise ValueError(f"Question {question_index} must be an object")
        question_text = _required_text(
            question.get("question"),
            label=f"Question {question_index} text",
            max_length=MAX_QUESTION_LENGTH,
        )

        answers = question.get("answers")
        if not isinstance(answers, list) or len(answers) < 2:
            raise ValueError(f"Question {question_index} must have at least 2 answers")
        if len(answers) > MAX_ANSWERS_PER_QUESTION:
            raise ValueError(
                f"Question {question_index} may have at most {MAX_ANSWERS_PER_QUESTION} answers"
            )

        cleaned_answers = []
        correct_count = 0
        for answer_index, answer in enumerate(answers, start=1):
            if not isinstance(answer, dict):
                raise ValueError(
                    f"Question {question_index}, answer {answer_index} must be an object"
                )
            answer_text = _required_text(
                answer.get("text"),
                label=f"Question {question_index}, answer {answer_index} text",
                max_length=MAX_ANSWER_LENGTH,
            )
            if not isinstance(answer.get("correct"), bool):
                raise ValueError(
                    f"Question {question_index}, answer {answer_index} must use true or false for correct"
                )
            correct = answer["correct"]
            correct_count += int(correct)
            cleaned_answers.append({"text": answer_text, "correct": correct})
        if correct_count == 0:
            raise ValueError(f"Question {question_index} must have at least 1 correct answer")

        raw_sources = question.get("sources") or []
        if not isinstance(raw_sources, list):
            raise ValueError(f"Question {question_index} sources must be an array")
        if len(raw_sources) > MAX_SOURCES_PER_QUESTION:
            raise ValueError(
                f"Question {question_index} may have at most {MAX_SOURCES_PER_QUESTION} sources"
            )

        cleaned_sources = []
        for source_index, source in enumerate(raw_sources, start=1):
            if not isinstance(source, dict):
                raise ValueError(
                    f"Question {question_index}, source {source_index} must be an object"
                )
            label = f"Question {question_index}, source {source_index}"
            cleaned_sources.append(
                {
                    "title": _optional_text(
                        source.get("title"),
                        label=f"{label} title",
                        max_length=MAX_SOURCE_TITLE_LENGTH,
                    ),
                    "url": _source_url(source.get("url"), label=f"{label} URL"),
                    "note": _optional_text(
                        source.get("note"),
                        label=f"{label} note",
                        max_length=MAX_SOURCE_NOTE_LENGTH,
                    ),
                }
            )

        raw_question_id = question.get("id", question_index)
        if isinstance(raw_question_id, bool) or not isinstance(raw_question_id, (int, str)):
            raw_question_id = question_index
        if isinstance(raw_question_id, str) and len(raw_question_id) > 64:
            raw_question_id = question_index

        cleaned_questions.append(
            {
                "id": raw_question_id,
                "question": question_text,
                "answers": cleaned_answers,
                "explanation": _optional_text(
                    question.get("explanation"),
                    label=f"Question {question_index} explanation",
                    max_length=MAX_EXPLANATION_LENGTH,
                ),
                "sources": cleaned_sources,
            }
        )

    return {"title": title, "questions": cleaned_questions}
