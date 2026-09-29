from dataclasses import dataclass

from .quiz_schema import validate_quiz_json


class InvalidSubmission(ValueError):
    pass


@dataclass(frozen=True)
class ScoreResult:
    score: int
    total: int
    answered_count: int
    feedback: list[dict]


def public_quiz_payload(content: dict) -> dict:
    """Build the player payload without answer keys or post-answer explanations."""

    quiz = validate_quiz_json(content)
    return {
        "title": quiz["title"],
        "questions": [
            {
                "index": question_index,
                "question": question["question"],
                "multiple": sum(answer["correct"] for answer in question["answers"]) > 1,
                "answers": [
                    {"index": answer_index, "text": answer["text"]}
                    for answer_index, answer in enumerate(question["answers"])
                ],
            }
            for question_index, question in enumerate(quiz["questions"])
        ],
    }


def score_submission(content: dict, payload: object) -> ScoreResult:
    """Validate selected answer indexes and score exclusively against server data."""

    quiz = validate_quiz_json(content)
    if not isinstance(payload, dict):
        raise InvalidSubmission("Request JSON must be an object")
    submitted_answers = payload.get("answers")
    if not isinstance(submitted_answers, list):
        raise InvalidSubmission("answers must be an array")
    if len(submitted_answers) > len(quiz["questions"]):
        raise InvalidSubmission("Too many question answers were submitted")

    selections: dict[int, set[int]] = {}
    for entry in submitted_answers:
        if not isinstance(entry, dict):
            raise InvalidSubmission("Each submitted answer must be an object")
        question_index = entry.get("question_index")
        answer_indices = entry.get("answer_indices")
        if isinstance(question_index, bool) or not isinstance(question_index, int):
            raise InvalidSubmission("question_index must be an integer")
        if question_index < 0 or question_index >= len(quiz["questions"]):
            raise InvalidSubmission("question_index is out of range")
        if question_index in selections:
            raise InvalidSubmission("Each question may only be submitted once")
        if not isinstance(answer_indices, list):
            raise InvalidSubmission("answer_indices must be an array")

        question_answers = quiz["questions"][question_index]["answers"]
        selected: set[int] = set()
        for answer_index in answer_indices:
            if isinstance(answer_index, bool) or not isinstance(answer_index, int):
                raise InvalidSubmission("answer indexes must be integers")
            if answer_index < 0 or answer_index >= len(question_answers):
                raise InvalidSubmission("answer index is out of range")
            if answer_index in selected:
                raise InvalidSubmission("An answer may only be selected once")
            selected.add(answer_index)
        selections[question_index] = selected

    score = 0
    answered_count = 0
    feedback = []
    for question_index, question in enumerate(quiz["questions"]):
        selected = selections.get(question_index, set())
        correct = {
            answer_index
            for answer_index, answer in enumerate(question["answers"])
            if answer["correct"]
        }
        if selected:
            answered_count += 1
        is_correct = bool(selected) and selected == correct
        score += int(is_correct)
        status = "correct" if is_correct else "wrong" if selected else "missed"
        feedback.append(
            {
                "question_index": question_index,
                "status": status,
                "correct_answer_indices": sorted(correct),
                "explanation": question["explanation"],
                "sources": question["sources"],
            }
        )

    return ScoreResult(
        score=score,
        total=len(quiz["questions"]),
        answered_count=answered_count,
        feedback=feedback,
    )
