# Raspberry Pi deployment with Cloudflare Tunnel

This runbook keeps the application checkout disposable while storing the SQLite database and backups in persistent system directories. Gunicorn listens only on `127.0.0.1:8001`; Cloudflare Tunnel publishes the HTTPS hostname.

The examples use Linux user `pi` and checkout `/home/pi/apps/cs50quiz`. Change both consistently if your host differs.

## 1. Prepare persistent data directories

```bash
sudo install -d -o pi -g www-data -m 0750 /var/lib/quizforger
sudo install -d -o pi -g www-data -m 0750 /var/backups/quizforger
```

### Existing deployment: move the database before pulling

Older revisions tracked `db.sqlite3` inside the checkout. Stop the service and preserve it before a pull that removes the tracked file:

```bash
sudo systemctl stop quizforger
cd /home/pi/apps/cs50quiz
. .venv/bin/activate
python - <<'PY'
import sqlite3
from pathlib import Path

source = sqlite3.connect("file:db.sqlite3?mode=ro", uri=True)
destination_path = Path("/var/backups/quizforger/pre-persistent-path.sqlite3")
destination = sqlite3.connect(destination_path)
source.backup(destination)
destination.close()
source.close()
print(destination_path)
PY
cp --preserve=mode,timestamps /var/backups/quizforger/pre-persistent-path.sqlite3 /var/lib/quizforger/db.sqlite3
chown pi:www-data /var/lib/quizforger/db.sqlite3
chmod 0640 /var/lib/quizforger/db.sqlite3
python - <<'PY'
import sqlite3
for path in ("/var/backups/quizforger/pre-persistent-path.sqlite3", "/var/lib/quizforger/db.sqlite3"):
    with sqlite3.connect(path) as connection:
        result = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if result != "ok":
        raise SystemExit(f"Integrity check failed for {path}: {result}")
    print(f"{path}: ok")
PY
```

Do not delete the old file until the new deployment and a new managed backup have both been verified. Pull the new revision only after this step.

## 2. Clone and install

```bash
sudo apt update
sudo apt install -y git python3-venv
mkdir -p /home/pi/apps
cd /home/pi/apps
git clone https://github.com/RuslanLomaka/cs50quiz.git
cd cs50quiz
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For an update, create and verify a backup first, then pull and install requirements again.

## 3. Configure production

```bash
if [ ! -f .env ]; then
  cp deployment/quizforger.env.example .env
  chmod 0600 .env
fi
python - <<'PY'
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
PY
```

Edit `.env` and set the real secret, hostname, trusted HTTPS origin, database path, and backup directory. On an existing deployment, merge the new variables into the existing file; never replace its secret with the example. Keep `DJANGO_SECURE_HSTS_SECONDS=0` until HTTPS is confirmed. A production start fails closed if `DJANGO_SECRET_KEY` is absent.

Prepare the application:

```bash
. .venv/bin/activate
set -a
. ./.env
set +a
if [ -f /var/lib/quizforger/db.sqlite3 ]; then python manage.py check_database; fi
python manage.py backup_database --if-exists --keep 30
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py check --deploy
```

Create an administrator when needed:

```bash
set -a
. ./.env
set +a
python manage.py createsuperuser
```

## 4. Install the application and backup services

```bash
sudo cp deployment/quizforger.service /etc/systemd/system/quizforger.service
sudo cp deployment/quizforger-backup.service /etc/systemd/system/quizforger-backup.service
sudo cp deployment/quizforger-backup.timer /etc/systemd/system/quizforger-backup.timer
sudo systemctl daemon-reload
sudo systemctl enable --now quizforger
sudo systemctl enable --now quizforger-backup.timer
sudo systemctl start quizforger-backup.service
sudo systemctl status quizforger quizforger-backup.timer
```

Verify the local application and the newest backup:

```bash
set -a
. ./.env
set +a
curl --fail -H 'X-Forwarded-Proto: https' http://127.0.0.1:8001/healthz
ls -l /var/backups/quizforger
python manage.py check_database
```

The service creates a verified backup before each start. The timer also runs daily and retains the newest 30 snapshots. Copy snapshots to another device or encrypted remote storage; same-disk backups do not protect against disk failure or theft.

## 5. Publish with Cloudflare Tunnel

Install `cloudflared` using the current official instructions for the Pi architecture. If a healthy connector already exists, add a published application route:

- hostname: the real quiz hostname
- service type: `HTTP`
- service URL: `localhost:8001`

For a new named tunnel:

```bash
cloudflared tunnel login
cloudflared tunnel create quizforger
cp deployment/cloudflared-config.example.yml ~/.cloudflared/config.yml
# Replace the UUID and hostname in the copied file.
cloudflared tunnel route dns quizforger quiz.example.com
sudo cloudflared --config /home/pi/.cloudflared/config.yml service install
sudo systemctl start cloudflared
```

After public HTTPS works, raise `DJANGO_SECURE_HSTS_SECONDS` deliberately (for example to `3600` first), restart QuizForger, and rerun `python manage.py check --deploy`.

## 6. Release an update manually

After completing the initial installation and the restore drill, release later versions from the Pi with:

```bash
cd /home/pi/apps/cs50quiz
bash deployment/deploy-on-host.sh
```

The script rejects local checkout changes and concurrent runs. Before fetching code it creates an integrity-checked SQLite backup; it then permits only a fast-forward to `origin/main`, installs dependencies, applies migrations, builds static files, runs production checks, restarts the service, and verifies `/healthz`.

## Restore drill

Restoration is intentionally manual and requires downtime:

```bash
sudo systemctl stop quizforger
cd /home/pi/apps/cs50quiz
. .venv/bin/activate
set -a
. ./.env
set +a
python manage.py backup_database --if-exists --keep 30
cp /var/backups/quizforger/CHOSEN_BACKUP.sqlite3 /var/lib/quizforger/db.sqlite3.restore
python - <<'PY'
import sqlite3
path = "/var/lib/quizforger/db.sqlite3.restore"
with sqlite3.connect(path) as connection:
    result = connection.execute("PRAGMA integrity_check").fetchone()[0]
if result != "ok":
    raise SystemExit(f"Restore candidate failed integrity check: {result}")
print("Restore candidate integrity: ok")
PY
mv /var/lib/quizforger/db.sqlite3.restore /var/lib/quizforger/db.sqlite3
chown pi:www-data /var/lib/quizforger/db.sqlite3
chmod 0640 /var/lib/quizforger/db.sqlite3
python manage.py migrate --noinput
python manage.py check_database
sudo systemctl start quizforger
curl --fail -H 'X-Forwarded-Proto: https' http://127.0.0.1:8001/healthz
```

Never restore over a running database. Keep the pre-restore backup until application behavior has been verified.
