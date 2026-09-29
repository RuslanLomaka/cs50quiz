# Raspberry Pi deployment with Cloudflare Tunnel

This runbook keeps code, configuration, live SQLite data, and backups in separate locations:

- application: `/srv/quizforger/app`
- environment: `/etc/quizforger/quizforger.env`
- database: `/var/lib/quizforger/db.sqlite3`
- backups: `/var/backups/quizforger`

The web process uses a dedicated `quizforger` account and cannot read personal home directories. Gunicorn listens only on `127.0.0.1:8001`; Cloudflare Tunnel publishes the HTTPS hostname.

## 1. Create the service account and persistent directories

```bash
id -u quizforger >/dev/null 2>&1 || sudo useradd \
  --system \
  --create-home \
  --home-dir /srv/quizforger \
  --shell /usr/sbin/nologin \
  quizforger
sudo install -d -o quizforger -g quizforger -m 0750 /srv/quizforger
sudo install -d -o quizforger -g quizforger -m 0700 /var/lib/quizforger
sudo install -d -o quizforger -g quizforger -m 0700 /var/backups/quizforger
sudo install -d -o root -g quizforger -m 0750 /etc/quizforger
```

### Existing deployment: preserve the formerly tracked database

Older revisions tracked `db.sqlite3` inside the checkout. Before pulling the revision that removes it, stop the old service and make two verified copies outside the checkout:

```bash
sudo systemctl stop quizforger
cd /home/pi/apps/cs50quiz
sudo python3 - <<'PY'
import sqlite3
from pathlib import Path

source_path = Path("db.sqlite3").resolve()
backup_path = Path("/var/backups/quizforger/pre-persistent-path.sqlite3")
with sqlite3.connect(f"{source_path.as_uri()}?mode=ro", uri=True) as source:
    with sqlite3.connect(backup_path) as destination:
        source.backup(destination)
PY
sudo install \
  -o quizforger -g quizforger -m 0600 \
  /var/backups/quizforger/pre-persistent-path.sqlite3 \
  /var/lib/quizforger/db.sqlite3
sudo chown quizforger:quizforger /var/backups/quizforger/pre-persistent-path.sqlite3
sudo chmod 0600 /var/backups/quizforger/pre-persistent-path.sqlite3
sudo python3 - <<'PY'
import sqlite3

for path in (
    "/var/backups/quizforger/pre-persistent-path.sqlite3",
    "/var/lib/quizforger/db.sqlite3",
):
    with sqlite3.connect(path) as connection:
        result = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if result != "ok":
        raise SystemExit(f"Integrity check failed for {path}: {result}")
    print(f"{path}: ok")
PY
```

Only after both copies report `ok`, restore the checkout copy to its tracked state and fast-forward. This prevents a locally changed tracked database from blocking the pull that removes it:

```bash
git restore --source=HEAD --worktree -- db.sqlite3
git pull --ff-only
```

Keep the old checkout and its external backup until the new installation, managed backup, and restore drill have all succeeded.

## 2. Clone and install

```bash
sudo apt update
sudo apt install -y curl git python3-venv util-linux
sudo -u quizforger git clone https://github.com/RuslanLomaka/cs50quiz.git /srv/quizforger/app
sudo -u quizforger python3 -m venv /srv/quizforger/app/.venv
sudo -u quizforger /srv/quizforger/app/.venv/bin/python -m pip install \
  -r /srv/quizforger/app/requirements.txt
```

## 3. Configure production

Install the example once, then edit the private copy. Never overwrite an existing production secret with the example.

```bash
sudo install \
  -o root -g quizforger -m 0640 \
  /srv/quizforger/app/deployment/quizforger.env.example \
  /etc/quizforger/quizforger.env
/srv/quizforger/app/.venv/bin/python - <<'PY'
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
PY
sudoedit /etc/quizforger/quizforger.env
```

Set the real secret, hostname, trusted HTTPS origin, database path, and backup directory. Keep `DJANGO_SECURE_HSTS_SECONDS=0` until public HTTPS is confirmed. A production start fails closed when the secret or persistent database is missing.

For the initial installation only, the database may not exist yet:

```bash
sudo -u quizforger bash -c '
  set -a
  . /etc/quizforger/quizforger.env
  set +a
  cd /srv/quizforger/app
  if [ -f "$DJANGO_DATABASE_PATH" ]; then .venv/bin/python manage.py check_database; fi
  .venv/bin/python manage.py backup_database --if-exists --keep 30
  .venv/bin/python manage.py migrate --noinput
  .venv/bin/python manage.py check_quizzes
  .venv/bin/python manage.py collectstatic --noinput
  .venv/bin/python manage.py check --deploy
'
```

Create an administrator when needed:

```bash
sudo -u quizforger bash -c '
  set -a
  . /etc/quizforger/quizforger.env
  set +a
  cd /srv/quizforger/app
  .venv/bin/python manage.py createsuperuser
'
```

## 4. Install the application and backup services

```bash
sudo cp /srv/quizforger/app/deployment/quizforger.service /etc/systemd/system/
sudo cp /srv/quizforger/app/deployment/quizforger-backup.service /etc/systemd/system/
sudo cp /srv/quizforger/app/deployment/quizforger-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now quizforger
sudo systemctl enable --now quizforger-backup.timer
sudo systemctl start quizforger-backup.service
sudo systemctl status quizforger quizforger-backup.timer
```

Verify the application, database, and newest backup:

```bash
curl --fail --max-time 5 \
  -H 'X-Forwarded-Proto: https' \
  http://127.0.0.1:8001/healthz
sudo -u quizforger bash -c '
  set -a
  . /etc/quizforger/quizforger.env
  set +a
  cd /srv/quizforger/app
  .venv/bin/python manage.py check_database
  .venv/bin/python manage.py check_quizzes
'
sudo ls -l /var/backups/quizforger
```

Backups run once per day and once per approved release, not on every service restart. This prevents a restart loop from consuming retention snapshots. Copy snapshots to another device or encrypted remote storage; same-disk backups do not protect against disk failure or theft.

## 5. Publish with Cloudflare Tunnel

Install `cloudflared` using Cloudflare's current instructions for the Pi architecture. The tunnel may run under a separate administrator account; `ProtectHome=true` prevents the QuizForger web process from reading that account's files.

Configure the published application route with:

- hostname: the real quiz hostname
- service type: `HTTP`
- service URL: `localhost:8001`

After public HTTPS works, raise `DJANGO_SECURE_HSTS_SECONDS` deliberately—start with `3600`—and restart QuizForger. Before later releases, use `31536000` only after HTTPS is proven stable and before enabling HSTS preload.

## 6. Release an update manually

The release script runs as `quizforger` but needs permission to restart only its own service. Confirm the `systemctl` path with `command -v systemctl`, then edit with `sudo visudo`:

```text
quizforger ALL=(root) NOPASSWD: /usr/bin/systemctl restart quizforger
```

Release from an administrator account:

```bash
sudo -u quizforger bash -c '
  cd /srv/quizforger/app
  bash deployment/deploy-on-host.sh
'
```

The script rejects local checkout changes, concurrent runs, and a missing persistent database. It verifies and backs up the database before fetching, permits only a fast-forward to `origin/main`, installs dependencies, applies migrations, validates all stored quizzes, builds static files, runs strict deployment checks, restarts the service, and performs a bounded health check.

## Restore drill

Restoration is intentionally manual and requires downtime. If the current database is healthy, create one final managed backup. If it is corrupt, preserve the corrupt file separately instead of letting a failed backup block recovery:

```bash
sudo systemctl stop quizforger
sudo -u quizforger bash -c '
  set -a
  . /etc/quizforger/quizforger.env
  set +a
  cd /srv/quizforger/app
  if .venv/bin/python manage.py check_database; then
    .venv/bin/python manage.py backup_database --keep 30
  else
    corrupt_copy="/var/backups/quizforger/corrupt-$(date -u +%Y%m%dT%H%M%SZ).sqlite3"
    cp --preserve=mode,timestamps "$DJANGO_DATABASE_PATH" "$corrupt_copy"
    chmod 0600 "$corrupt_copy"
    echo "Preserved corrupt database at $corrupt_copy"
  fi
  install -m 0600 \
    /var/backups/quizforger/CHOSEN_BACKUP.sqlite3 \
    "$DJANGO_DATABASE_PATH.restore"
  .venv/bin/python - <<PY
import os
import sqlite3

path = os.environ["DJANGO_DATABASE_PATH"] + ".restore"
with sqlite3.connect(path) as connection:
    result = connection.execute("PRAGMA integrity_check").fetchone()[0]
if result != "ok":
    raise SystemExit(f"Restore candidate failed integrity check: {result}")
print("Restore candidate integrity: ok")
PY
  mv "$DJANGO_DATABASE_PATH.restore" "$DJANGO_DATABASE_PATH"
  .venv/bin/python manage.py migrate --noinput
  .venv/bin/python manage.py check_database
  .venv/bin/python manage.py check_quizzes
'
sudo systemctl start quizforger
curl --fail --max-time 5 \
  -H 'X-Forwarded-Proto: https' \
  http://127.0.0.1:8001/healthz
```

Never restore over a running database. Keep the pre-restore or corrupt copy until application behavior has been verified.
