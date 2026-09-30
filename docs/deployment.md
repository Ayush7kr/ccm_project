# CCM — Production Deployment & Operations Guide

This document describes how to deploy **CCM (Campaign Call Manager)** to a production environment using Docker Compose or traditional Linux (Ubuntu/Debian) virtual machines.

---

## 1. Production Architecture Overview

```text
                  Internet (HTTPS :443)
                            │
                            ▼
              Nginx / Reverse Proxy (SSL Termination)
             ├── /static/  ──► Serve static files directly
             ├── /media/   ──► Serve media files directly
             └── /         ──► Proxy pass to Gunicorn (127.0.0.1:8000)
                                      │
                                      ▼
                        Gunicorn WSGI Application Server
                                (3 Workers)
                                      │
                                      ▼
                        CCM Django Core Application
                                      │
                                      ▼
                        PostgreSQL Database Server
```

---

## 2. Option A: Deployment with Docker Compose (Recommended)

CCM includes a ready-to-use [`Dockerfile`](file:///f:/CCM/Dockerfile) and [`docker-compose.yml`](file:///f:/CCM/docker-compose.yml).

### Step 1: Configure Production `.env`
Create a `.env` file in the project root:
```env
DEBUG=False
SECRET_KEY=generate-a-strong-64-character-secret-key-here
ALLOWED_HOSTS=ccm.yourcompany.com
CSRF_TRUSTED_ORIGINS=https://ccm.yourcompany.com
DATABASE_URL=postgresql://ccm_user:StrongPassword123@db:5432/ccm_db
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-api-key
DEFAULT_FROM_EMAIL=noreply@ccm.yourcompany.com
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### Step 2: Build and Launch Containers
```bash
docker compose up -d --build
```

### Step 3: Run Database Migrations Inside Container
```bash
docker compose exec web python manage.py migrate
```

### Step 4: Collect Static Assets
```bash
docker compose exec web python manage.py collectstatic --noinput
```

---

## 3. Option B: Traditional Linux (Ubuntu/Debian) Deployment

### Step 1: Install System Packages
```bash
sudo apt update && sudo apt install -y python3-venv python3-pip postgresql libpq-dev nginx
```

### Step 2: Provision PostgreSQL Database
```bash
sudo -u postgres psql
```
```sql
CREATE DATABASE ccm_db;
CREATE USER ccm_user WITH PASSWORD 'StrongPassword123';
ALTER ROLE ccm_user SET client_encoding TO 'utf8';
ALTER ROLE ccm_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE ccm_user SET timezone TO 'Asia/Kolkata';
GRANT ALL PRIVILEGES ON DATABASE ccm_db TO ccm_user;
\q
```

### Step 3: Setup Virtual Environment & Dependencies
```bash
git clone <repository_url> /var/www/ccm
cd /var/www/ccm
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

### Step 4: Migrate & Collect Static Files
```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

### Step 5: Configure Systemd Service for Gunicorn
Create `/etc/systemd/system/ccm.service`:
```ini
[Unit]
Description=CCM Gunicorn Daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/ccm
ExecStart=/var/www/ccm/venv/bin/gunicorn \
          --workers 3 \
          --bind 127.0.0.1:8000 \
          --timeout 60 \
          config.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```
Start and enable the service:
```bash
sudo systemctl daemon-reload
sudo systemctl start ccm
sudo systemctl enable ccm
```

### Step 6: Configure Nginx Reverse Proxy
Create `/etc/nginx/sites-available/ccm`:
```nginx
server {
    listen 80;
    server_name ccm.yourcompany.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ccm.yourcompany.com;

    ssl_certificate /etc/letsencrypt/live/ccm.yourcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ccm.yourcompany.com/privkey.pem;

    client_max_body_size 25M;

    location /static/ {
        alias /var/www/ccm/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    location /media/ {
        alias /var/www/ccm/media/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```
Enable the site and reload Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/ccm /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 4. Production Security Checklist

- [ ] `DEBUG = False` verified in production `.env`.
- [ ] `SECRET_KEY` set to a unique, random string stored outside source control.
- [ ] `ALLOWED_HOSTS` configured with exact domain names.
- [ ] `SECURE_SSL_REDIRECT = True` active.
- [ ] `SESSION_COOKIE_SECURE = True` and `CSRF_COOKIE_SECURE = True`.
- [ ] Database credentials verified and limited to `ccm_user`.
- [ ] HTTPS certificates configured with auto-renewal (e.g. Certbot Let's Encrypt).
- [ ] Production health check verified at `https://ccm.yourcompany.com/health/`.
