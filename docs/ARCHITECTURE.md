# QuizForger architecture

## Product boundary

QuizForger is a self-hostable quiz authoring and playing service. Authors import AI-generated quiz JSON, refine it in a browser editor, and publish quizzes. Players may be authenticated or anonymous. Django owns identity, authorization, validation, scoring, persistence, and public statistics.

## Main components

- `config/`: settings, routing, request correlation, and structured logging.
- `quizforger/quiz_schema.py`: bounded import validation and canonicalization.
- `quizforger/scoring.py`: public player serialization and server-side grading.
- `quizforger/storage.py`: quiz creation, updates, and reversible archival.
- `quizforger/views.py`: thin HTTP orchestration and authorization.
- `quizforger/database_backups.py`: verified online SQLite snapshots.
- `quizforger/static/quizforger/quiz.js`: rendering and submission of answer indexes; it never receives the answer key before grading.

## Quiz lifecycle

1. An authenticated author submits pasted JSON.
2. The schema layer applies size, count, type, text-length, and URL limits and returns a canonical document.
3. Storage assigns a collision-resistant ID and saves the quiz.
4. The public quiz API removes answer keys, explanations, and sources.
5. The player submits selected question/answer indexes plus an idempotency UUID.
6. The scoring service grades against persisted content. Only then does the API return score and feedback.
7. Deletion in the UI archives a quiz. Attempts remain available for recovery and audit.

## Data durability

SQLite remains a reasonable default for a single low-traffic Raspberry Pi. The production database path is outside the Git checkout. The service creates an online, integrity-checked backup before startup, and a systemd timer repeats the backup daily. Retention keeps the newest 30 snapshots.

This reduces data-loss risk but cannot guarantee zero loss. Backups must also be copied off-device and restore drills must be performed. PostgreSQL is the recommended next step for multiple app hosts or sustained concurrent writes.

## Observability

Every response receives an `X-Request-ID`. Application events are JSON logs with identifiers and counts but no email addresses, passwords, cookies, raw quiz content, or selected answers. Setting `SENTRY_DSN` enables error reporting without default personally identifiable information. Health checks verify database connectivity at `/healthz`.
