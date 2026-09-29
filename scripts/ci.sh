#!/usr/bin/env bash
set -Eeuo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

if [[ -n "${PYTHON_BIN:-}" ]]; then
    python_bin="$PYTHON_BIN"
elif [[ -x "$project_root/.venv/bin/python" ]]; then
    python_bin="$project_root/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    python_bin="$(command -v python3)"
else
    python_bin="$(command -v python)"
fi

mkdir -p test-results

"$python_bin" -m ruff check .
"$python_bin" -m ruff format --check .
"$python_bin" manage.py makemigrations --check --dry-run
"$python_bin" manage.py migrate --noinput

"$python_bin" -m coverage erase
"$python_bin" -m coverage run -m pytest --junitxml=test-results/pytest.xml
"$python_bin" -m coverage report
"$python_bin" -m coverage xml -o coverage.xml
# Audit the fully resolved virtual environment, including transitive and CI dependencies.
"$python_bin" -m pip_audit --local

node --check quizforger/static/quizforger/quiz.js

export DJANGO_DEBUG=False
export DJANGO_SECRET_KEY="ci-only-secret-key-that-is-never-used-outside-ci-123456789"
export DJANGO_ALLOWED_HOSTS="localhost"
export DJANGO_SECURE_HSTS_SECONDS="3600"
export DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=True
export DJANGO_SECURE_HSTS_PRELOAD=True

"$python_bin" manage.py collectstatic --noinput
"$python_bin" manage.py check --deploy --fail-level WARNING
