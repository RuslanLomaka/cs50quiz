def quiz_document() -> dict:
    return {
        "title": "Safe quiz",
        "questions": [
            {
                "id": 1,
                "question": "Which values are even?",
                "answers": [
                    {"text": "2", "correct": True},
                    {"text": "3", "correct": False},
                    {"text": "4", "correct": True},
                ],
                "explanation": "Even numbers divide by two without a remainder.",
                "sources": [
                    {
                        "title": "Example",
                        "url": "https://example.com/even",
                        "note": "Background reading",
                    }
                ],
            },
            {
                "id": 2,
                "question": "Two plus two?",
                "answers": [
                    {"text": "4", "correct": True},
                    {"text": "5", "correct": False},
                ],
                "explanation": "2 + 2 = 4.",
                "sources": [],
            },
        ],
    }
