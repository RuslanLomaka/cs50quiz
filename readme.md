# QuizForger

[![CI](https://github.com/RuslanLomaka/cs50quiz/actions/workflows/ci.yml/badge.svg)](https://github.com/RuslanLomaka/cs50quiz/actions/workflows/ci.yml)

QuizForger is a self-hostable Django application for authoring, refining, publishing, and playing quizzes. An author can ask an AI tool for quiz JSON, import the result, and edit it in a structured browser UI. Players receive immediate feedback while the server records trustworthy aggregate results.

It began as a CS50 Web capstone and is now being hardened as an open-source product.

## Current capabilities

- signup and email-or-username login
- authenticated quiz import, visual editing, and reversible archival
- public quiz play for guests and signed-in users
- single- and multiple-answer questions
- server-side scoring; correct answers are not sent before submission
- idempotent attempt recording and public attempt/average statistics
- explanations and validated `http`/`https` sources after grading
- English, German, and Ukrainian UI/prompt catalogs
- system and manual light/dark themes
- structured JSON logs, request IDs, health checks, and optional Sentry reporting
- integrity-checked SQLite backups with systemd scheduling

## Trust and data model

The browser is presentation code, not a source of truth. It submits selected answer indexes; Django validates and grades them against stored quiz content. Imports are bounded by request size, question/answer/source counts, text lengths, and URL rules. UI deletion archives a quiz so attempts are retained.

SQLite is the default for a single low-traffic host. Production data lives outside the Git checkout and is backed up before service start and every day. This reduces risk, but zero data loss cannot be guaranteed: copy backups off-device and test restoration. See [the architecture](docs/ARCHITECTURE.md) and [deployment runbook](deployment/README.md).

## Local setup

Python 3.10 or newer is required.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Open `http://127.0.0.1:8000/quizzes`.

Runtime-only installation:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Verification

Run the complete Windows quality gate:

```powershell
.\scripts\verify.ps1
```

Or run individual checks:

```powershell
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe -m coverage run -m pytest
.\.venv\Scripts\python.exe -m coverage report
.\.venv\Scripts\python.exe -m pip_audit --local
```

GitHub Actions tests Python 3.10, 3.12, and 3.14. Its quality job uses `scripts/ci.sh` for linting, migration drift, tests, coverage, static assets, JavaScript syntax, production checks, and runtime dependency auditing. See the [deployment runbook](deployment/README.md) before releasing to a Raspberry Pi.

## Production configuration

Copy `deployment/quizforger.env.example` to a private `.env` file and set at least:

- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_DATABASE_PATH` to a persistent path outside the checkout
- `QUIZFORGER_BACKUP_DIR` to a separate backup directory

`SENTRY_DSN` is optional. Logs never intentionally include email addresses, cookies, passwords, raw quiz imports, or answer selections.

Useful operational commands:

```powershell
.\.venv\Scripts\python.exe manage.py check_database
.\.venv\Scripts\python.exe manage.py backup_database --keep 30
```

## Project layout

- `config/` — Django settings, routing, request IDs, and log formatting
- `quizforger/quiz_schema.py` — import validation and canonicalization
- `quizforger/scoring.py` — public serialization and server-side grading
- `quizforger/storage.py` — quiz write operations and archival
- `quizforger/database_backups.py` — verified SQLite snapshots
- `quizforger/views.py` — HTTP orchestration and authorization
- `quizforger/tests/` — unit, API, authorization, and backup tests
- `deployment/` — systemd, Cloudflare Tunnel, backup, and deployment automation
- `docs/` — architecture and the full engineering review

## CS50W distinctiveness and complexity

QuizForger is not a clone of the course social-network, commerce, email, or wiki projects. Its core workflow combines AI-assisted structured import, a visual quiz editor, public interactive play, ownership rules, trusted server-side grading, stored attempts, and aggregate statistics. The application crosses Django models, authentication, authorization, JSON validation, browser state, database persistence, responsive UI, deployment, backup, and operational observability concerns.

## Open-source status

Issues and pull-request templates, a security policy, CI, and contribution guidance are included. A license has not yet been selected, so the repository is source-visible but is not legally ready to accept third-party contributions. The decision and remaining product priorities are documented in [the engineering review](docs/CODE_REVIEW.md).

## Author

Ruslan Lomaka — [portfolio](https://work.ruslanlomaka.org) · [LinkedIn](https://www.linkedin.com/in/ruslan-lomaka/)
