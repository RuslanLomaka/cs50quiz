# Raspberry Pi deployment with Cloudflare Tunnel

This app should run behind a real WSGI server on the Pi. Do not expose Django's development server to the internet.

## Assumptions

- Raspberry Pi OS or another Debian-based Linux install.
- The app will live at `/home/pi/apps/cs50quiz`.
- Gunicorn listens only on `127.0.0.1:8001`.
- Cloudflare Tunnel publishes the app hostname and forwards traffic to Gunicorn.

If your Linux user is not `pi`, update `deployment/quizforger.service` before installing it.

## 1. Clone and install the app

```bash
sudo apt update
sudo apt install -y git python3-venv

mkdir -p /home/pi/apps
cd /home/pi/apps
git clone https://github.com/RuslanLomaka/cs50quiz.git
cd cs50quiz

python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 2. Configure production environment

```bash
cp deployment/quizforger.env.example .env
python - <<'PY'
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
PY
```

Edit `.env` and set:

- `DJANGO_SECRET_KEY` to the generated value.
- `DJANGO_ALLOWED_HOSTS` to your real Cloudflare hostname.
- `DJANGO_CSRF_TRUSTED_ORIGINS` to `https://your-real-hostname`.
- Leave `DJANGO_SECURE_HSTS_SECONDS=0` for the first deployment. After HTTPS is confirmed, you can raise it deliberately.

## 3. Prepare Django

```bash
. .venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
```

Create an admin user if needed:

```bash
python manage.py createsuperuser
```

## 4. Install the app service

```bash
sudo cp deployment/quizforger.service /etc/systemd/system/quizforger.service
sudo systemctl daemon-reload
sudo systemctl enable --now quizforger
sudo systemctl status quizforger
```

Local health check:

```bash
curl -I http://127.0.0.1:8001/quizzes
```

## 5. Install and configure Cloudflare Tunnel

Install `cloudflared` using the current command shown in the Cloudflare dashboard or Cloudflare package repository for your Pi architecture.

Authenticate and create a named tunnel:

```bash
cloudflared tunnel login
cloudflared tunnel create quizforger
cloudflared tunnel list
```

Copy the example config and replace the UUID and hostname:

```bash
cp deployment/cloudflared-config.example.yml ~/.cloudflared/config.yml
nano ~/.cloudflared/config.yml
```

Route DNS through Cloudflare:

```bash
cloudflared tunnel route dns quizforger quiz.example.com
```

Install and start the tunnel service:

```bash
sudo cloudflared --config /home/pi/.cloudflared/config.yml service install
sudo systemctl start cloudflared
sudo systemctl status cloudflared
```

After this, open `https://quiz.example.com/quizzes`.

## Operational notes

- Keep inbound router ports closed. Cloudflare Tunnel only needs outbound connectivity.
- Back up `db.sqlite3` before deploys if you keep SQLite in production.
- For a public site with real users, plan a later move from SQLite to PostgreSQL.
- Rotate the committed development `SECRET_KEY`; production must use `.env`.
