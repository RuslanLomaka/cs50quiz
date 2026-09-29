# Contributing to QuizForger

QuizForger is being prepared as an open-source product. A repository license still needs to be selected before third-party contributions can be accepted; see `docs/CODE_REVIEW.md`.

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Never commit `.env`, `*.sqlite3`, backups, logs, or real user/quiz data. Use generated test fixtures.

## Quality gate

On Windows, run:

```powershell
.\scripts\verify.ps1
```

Every behavior change should include a focused automated test. Database migrations must be reversible where practical and tested against a verified backup. Security-sensitive changes should explain their trust boundary in the pull request.

## Pull requests

Keep pull requests focused. Explain the user problem, verification, data impact, and rollback path. Avoid adding a dependency when the standard library or Django already provides a clear, maintainable solution.
