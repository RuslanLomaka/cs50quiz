#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
app_dir="${QUIZFORGER_APP_DIR:-$(cd "$script_dir/.." && pwd)}"
cd "$app_dir"

for required_command in curl flock git sudo; do
    if ! command -v "$required_command" >/dev/null 2>&1; then
        echo "Required command is unavailable: $required_command" >&2
        exit 1
    fi
done

exec 9>"$app_dir/.deploy.lock"
if ! flock -n 9; then
    echo "Another QuizForger deployment is already running." >&2
    exit 1
fi

env_file="${QUIZFORGER_ENV_FILE:-/etc/quizforger/quizforger.env}"
if [[ ! -f "$env_file" ]]; then
    echo "Production environment file is missing: $env_file" >&2
    exit 1
fi

python_bin="$app_dir/.venv/bin/python"
if [[ ! -x "$python_bin" ]]; then
    echo "Python virtual environment is missing: $python_bin" >&2
    exit 1
fi

worktree_changes="$(git status --porcelain --untracked-files=normal)"
if [[ -n "$worktree_changes" ]]; then
    echo "Deployment refused because the production checkout has local changes:" >&2
    printf '%s\n' "$worktree_changes" >&2
    exit 1
fi

set -a
# The production file is private and maintained by the host administrator.
# shellcheck disable=SC1091
. "$env_file"
set +a

: "${DJANGO_DATABASE_PATH:?DJANGO_DATABASE_PATH must be set in $env_file}"
if [[ ! -f "$DJANGO_DATABASE_PATH" ]]; then
    echo "Deployment refused because the persistent database is missing: $DJANGO_DATABASE_PATH" >&2
    exit 1
fi

before_revision="$(git rev-parse HEAD)"
echo "Backing up the database before deploying from $before_revision"
"$python_bin" manage.py check_database
"$python_bin" manage.py backup_database --keep 30

git fetch --prune origin main
if ! git merge-base --is-ancestor HEAD origin/main; then
    echo "Deployment refused: the production checkout cannot fast-forward to origin/main." >&2
    exit 1
fi
git merge --ff-only origin/main
after_revision="$(git rev-parse HEAD)"

"$python_bin" -m pip install --disable-pip-version-check -r requirements.txt
"$python_bin" manage.py migrate --noinput
"$python_bin" manage.py check_quizzes
"$python_bin" manage.py collectstatic --noinput
"$python_bin" manage.py check --deploy --fail-level WARNING
"$python_bin" manage.py check_database

sudo -n systemctl restart quizforger
curl \
    --fail \
    --connect-timeout 2 \
    --max-time 5 \
    --retry 10 \
    --retry-all-errors \
    --retry-delay 2 \
    --show-error \
    --silent \
    -H 'X-Forwarded-Proto: https' \
    http://127.0.0.1:8001/healthz >/dev/null

echo "QuizForger deployment healthy: $before_revision -> $after_revision"
