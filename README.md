# CCM — Campaign Call Manager

A modern, production-ready tele-calling campaign and customer communication management platform built with **Python 3.12**, **Django**, and **Vanilla JavaScript/CSS**. Designed for organizations to orchestrate structured calling campaigns, streamline lead assignment, capture questionnaire responses during live calls, and extract actionable operational intelligence.

<p align="center">
  <img src="docs/screenshots/landing_page.png" alt="CCM Public Landing Page" width="850">
</p>
<p align="center">
  <em>Public Landing Page featuring modern hero design, value propositions, and direct portal access.</em>
</p>

---

## 🖼️ Interface Showcase

| Admin Operations Dashboard | Tele-caller Personal Workspace |
| :---: | :---: |
| ![Admin Dashboard](docs/screenshots/admin_dashboard.png) | ![Tele-caller Workspace](docs/screenshots/telecaller_dashboard.png) |
| *Real-time KPIs, campaign progress, and administration* | *Today's call queue, active leads, and callback scheduler* |

| Live Call Console & Questionnaires | Analytics & Operational Intelligence |
| :---: | :---: |
| ![Live Calling Console](docs/screenshots/telecaller_call_logging.png) | ![Analytics Dashboard](docs/screenshots/analytics_dashboard.png) |
| *Live stopwatch timer, outcome selector, dynamic survey* | *Chart.js outcome donuts, call trends, and agent productivity* |

---

## 🌟 Key Features

### 1. Public Landing Page (`/`)
- Public-facing welcome portal introducing CCM without requiring authentication.
- Highlights core capabilities: Campaign Management, Customer Directory, Live Calling Console, Questionnaires, Follow-up Tracking, and Report Center.
- Role-based architecture overview and direct sign-in entry point.

<p align="center">
  <img src="docs/screenshots/landing_page.png" alt="Public Landing Page" width="800">
</p>

### 2. Role-Based Access Control (RBAC) & Multi-Portal Architecture
- **Interactive Role Selector**: Intuitive role selection portal with dedicated Administrator and Tele-caller access cards.
- **Admin Portal**: Full oversight of campaigns, customer databases, tele-caller workforce, dynamic questionnaires, bulk assignments, centralized analytics, and Report Center.
- **Tele-caller Workspace**: Streamlined to assigned leads, live calling console with stopwatch duration timer, dynamic questionnaire logging, and callback scheduling.
- **Strict Role Security**: Enforced via decorators (`@admin_required`, `@telecaller_required`), object-level filtering, and custom 403 Forbidden handlers.

<p align="center">
  <img src="docs/screenshots/login_role_selection.png" alt="Role Selection and Login" width="750">
</p>

### 3. Dynamic Questionnaire Builder
- Dynamic question creation attached to campaigns supporting 5 question types:
  1. **Single Choice** (radio options)
  2. **Multiple Choice** (checkbox options)
  3. **Rating Scale** (1–5 Star Rating)
  4. **Open Ended** (text responses)
  5. **Yes / No** (binary choice)
- Interactive **Tele-caller Live Preview Mode** for verifying question layout.

### 4. Tele-caller Live Call Console & Response Logging
- Complete call outcome logger (Completed, No Answer, Unreachable, Busy, Follow-up Required).
- Live call stopwatch timer (Start / Pause / Auto-log).
- Automatic questionnaire display upon completing calls with instantaneous response saving.
- Integrated follow-up callback scheduler with automated overdue detection.

<p align="center">
  <img src="docs/screenshots/telecaller_call_logging.png" alt="Telecaller Live Call Console" width="800">
</p>

### 5. Customer & Lead Directory with Bulk Import & Assignment
- Upload `.csv` or `.xlsx` files with column validation & duplicate phone number detection.
- Pre-import preview with auto-enrollment into target campaigns.
- Flexible round-robin and manual lead assignment to tele-callers.
- Downloadable sample CSV template.

| CSV/XLSX Bulk Lead Ingestion | Lead Assignment to Tele-callers |
| :---: | :---: |
| ![Customer Import Engine](docs/screenshots/customer_import.png) | ![Customer Lead Assignment](docs/screenshots/customer_assign.png) |

### 6. Centralized Analytics Engine (`analytics/engine.py`)
- 100% database-derived unified metrics across dashboards, analytics views, and exports.
- Global date range filters: `Today`, `Last 7 Days`, `Last 30 Days`, `This Month`, `Last Month`, and `Custom Range`.
- Campaign filter isolating metrics, outcomes, and questionnaire response trends.
- Interactive Chart.js visualizations: Call Outcome Donut chart and Call Activity dual-line trend.
- Operational metrics: Campaign completion tracking (capped at 100%), tele-caller productivity table, customer response insights, and follow-up workload breakdowns.

<p align="center">
  <img src="docs/screenshots/analytics_dashboard.png" alt="Analytics and Visualizations" width="800">
</p>

### 7. Interactive Report Center & Multi-Format Exports
- 5 comprehensive business reports:
  1. Campaign Summary Report
  2. Call Activity Report
  3. Tele-caller Performance Report
  4. Customer Response Report
  5. Follow-up Schedule Report
- Multi-criteria filtering (Campaign, Tele-caller, Status, Date Range) with pre-export record count preview.
- **PDF Report Generation**: Built with ReportLab, featuring corporate headers, metadata, KPI summaries, and alternating row tables.
- **Excel Workbook Export**: Built with `openpyxl`, with styled dark headers, bold tokens, and auto-adjusted column widths.

<p align="center">
  <img src="docs/screenshots/reports_center.png" alt="Report Center and Exports" width="800">
</p>

### 8. Work Management: Team, Calls & Follow-ups

| Tele-caller Workforce Directory | Call History Records | Follow-up Callback Queue |
| :---: | :---: | :---: |
| ![Tele-callers Roster](docs/screenshots/telecallers_management.png) | ![Call History Records](docs/screenshots/call_records.png) | ![Follow-up Callbacks](docs/screenshots/followups_list.png) |
| *Agent status & metrics* | *Outcome badges & call times* | *Pending & overdue callbacks* |

### 9. Production Hardening & Health Monitoring
- Environment variable configuration for secrets, hosts, and database URLs.
- Secure cookie and session flags (`HttpOnly`, `SameSite=Lax`, conditional `Secure` in production).
- Security headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`.
- Dedicated health check endpoint: `/health/` verifying web server and database connectivity.

---

## 🛠️ Technology Stack

- **Backend Framework**: Python 3.12, Django 6.1
- **Database**: SQLite (Development) / PostgreSQL (Production-ready via `DATABASE_URL`)
- **Frontend UI**: Vanilla HTML5 (No Django Forms), Modular CSS3 (Design Tokens, Light/Dark Themes), Vanilla JavaScript
- **Icons & Visuals**: Lucide Icons
- **Charting Engine**: Chart.js
- **PDF Generation**: ReportLab
- **Excel Processing**: openpyxl
- **WSGI Server**: Gunicorn
- **Containerization**: Docker & Docker Compose

---

## 📁 Project Structure

```
f:/CCM/
├── manage.py
├── config/
│   ├── settings.py         # Development & production settings
│   ├── urls.py             # Root routing, public landing, auth, health
│   ├── wsgi.py             # WSGI entrypoint
│   └── asgi.py             # ASGI entrypoint
├── accounts/               # Custom User model, auth views, RBAC decorators
├── campaigns/              # Campaign CRUD & dynamic questionnaire builder
├── customers/              # Customer roster, CSV/XLSX import & lead assignment
├── calls/                  # Calling console, call outcomes, responses & follow-ups
├── analytics/              # Centralized analytics engine, reports, PDF/Excel views
├── templates/              # Templates & component partials
│   ├── public/             # Public landing page (home.html)
│   ├── auth/               # Login view
│   ├── components/         # Navbar, sidebar, alerts
│   ├── dashboard/          # Admin & tele-caller dashboards
│   ├── campaigns/          # Campaign views
│   ├── customers/          # Customer views & import preview
│   ├── telecallers/        # Tele-caller roster
│   ├── questionnaires/     # Questionnaire builder & preview
│   ├── calls/              # Live calling console & records
│   ├── followups/          # Follow-up callback list
│   ├── analytics/          # Analytics dashboard
│   ├── reports/            # Report center
│   └── notifications/      # Notification list
├── static/                 # CSS design system & JavaScript
│   ├── css/main.css        # Design tokens, layouts, cards, buttons
│   └── js/main.js          # Lucide icons, theme toggle, stopwatch
├── Dockerfile              # Multi-stage production container
├── docker-compose.yml      # Local container orchestration with PostgreSQL
├── .env.example            # Sample environment variables
└── README.md
```

---

## 🚀 Local Development Setup

### 1. Prerequisites
- Python 3.10+ installed
- Git (optional)

### 2. Create and Activate Virtual Environment
```bash
# Windows PowerShell
python -m venv venv
.\venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
Copy the sample environment file:
```bash
cp .env.example .env
```
*(For local development, default values with SQLite will work out of the box).*

### 5. Apply Database Migrations
```bash
python manage.py migrate
```

### 6. Seed Realistic Demo Data
Populate the database with realistic campaigns, tele-callers, customers, questions, calls, and follow-ups:
```bash
python manage.py seed_data
```

### 7. Run the Development Server
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser.

---

## 🔑 Demo User Accounts

| Role | Username | Password | Access Rights |
|---|---|---|---|
| **Administrator** | `admin` | `admin123` | Full access: Campaigns, Tele-callers, Customers, Analytics, Reports, Exports |
| **Tele-caller 1** | `rahul` | `telecaller123` | Assigned Campaigns & Leads, Calling Console, Personal Follow-ups |
| **Tele-caller 2** | `priya` | `telecaller123` | Assigned Campaigns & Leads, Calling Console, Personal Follow-ups |
| **Tele-caller 3** | `arjun` | `telecaller123` | Assigned Campaigns & Leads, Calling Console, Personal Follow-ups |
| **Tele-caller 4** | `sneha` | `telecaller123` | Assigned Campaigns & Leads, Calling Console, Personal Follow-ups |
| **Tele-caller 5** | `telecaller1` | `telecaller123` | Assigned Campaigns & Leads, Calling Console, Personal Follow-ups |

To create a new superuser manually:
```bash
python manage.py createsuperuser
```

---

## 🧪 Running Automated Tests

Run the full Django test suite:
```bash
python manage.py test
```

Run tests for specific applications:
```bash
python manage.py test accounts
python manage.py test analytics
python manage.py test campaigns
python manage.py test customers
python manage.py test calls
```

---

## 🐳 Docker & Production Deployment

### 1. Running with Docker Compose (Django + PostgreSQL)
```bash
docker-compose up --build -d
```
This launches:
- `db`: PostgreSQL 16 on port 5432
- `web`: Gunicorn server with 3 workers on port 8000, running migrations and static collection automatically

Check container health:
```bash
curl http://localhost:8000/health/
```

### 2. Manual Production Deployment on Linux VM

1. Set production environment variables in `.env`:
   ```ini
   DEBUG=False
   SECRET_KEY=generate-a-strong-random-key
   ALLOWED_HOSTS=ccm.yourdomain.com,your-server-ip
   CSRF_TRUSTED_ORIGINS=https://ccm.yourdomain.com
   DATABASE_URL=postgresql://ccm_user:password@localhost:5432/ccm_db
   SESSION_COOKIE_SECURE=True
   CSRF_COOKIE_SECURE=True
   SECURE_SSL_REDIRECT=True
   ```

2. Collect static assets:
   ```bash
   python manage.py collectstatic --noinput
   ```

3. Run with Gunicorn:
   ```bash
   gunicorn --bind 0.0.0.0:8000 --workers 3 config.wsgi:application
   ```

4. Configure Nginx as a reverse proxy forwarding requests to Gunicorn and serving `/static/` and `/media/`.

---

## 📋 System Health Endpoint

`GET /health/`
- **Authentication**: None required
- **Response**:
  ```json
  {
    "status": "healthy",
    "database": "connected"
  }
  ```
- **HTTP Status**: `200 OK` (or `503 Service Unavailable` if database is down).

---

## 📚 Comprehensive Documentation Index

Full documentation is available in the [`docs/`](file:///f:/CCM/docs) directory:

- [System Architecture](file:///f:/CCM/docs/architecture.md) — High-level architecture, module breakdown, request lifecycle, and sequence diagrams.
- [Setup & Installation](file:///f:/CCM/docs/setup.md) — Prerequisites, step-by-step installation, seeding data, and running the server.
- [Authentication & Password Security](file:///f:/CCM/docs/authentication.md) — Role selection, server-side validation, password hashing, and tokenized reset.
- [Role-Based Access Control (RBAC)](file:///f:/CCM/docs/role-based-access.md) — Permissions matrix, decorators, and object-level data isolation.
- [Database & Data Models](file:///f:/CCM/docs/database.md) — ER diagram, model specifications, fields, and constraints.
- [API & Endpoints Reference](file:///f:/CCM/docs/api.md) — Health check, analytics JSON feeds, and export endpoints.
- [Features & Capabilities](file:///f:/CCM/docs/features.md) — Detailed functional walk-through of all modules.
- [Testing & Quality Assurance](file:///f:/CCM/docs/testing.md) — Test suite execution, test cases, and manual QA checklists.
- [Production Deployment](file:///f:/CCM/docs/deployment.md) — Docker Compose, systemd, Nginx, and production checklists.
- [Troubleshooting & FAQ](file:///f:/CCM/docs/troubleshooting.md) — Common issues, causes, and solutions.
- [Security Architecture](file:///f:/CCM/docs/security.md) — Defense-in-depth, headers, cookies, CSRF, and IDOR mitigation.
- [Changelog](file:///f:/CCM/CHANGELOG.md) — Historical and recent development changes.
- [Contributing Guidelines](file:///f:/CCM/CONTRIBUTING.md) — Coding conventions, standards, and pull request rules.

---

## 🔒 Security Notes

- **Password Hashing**: PBKDF2 with SHA-256 (870,000 rounds).
- **Direct Password Overwrite Elimination**: Tele-caller edit form contains no password fields; passwords must be reset via cryptographic HMAC tokens emailed to the user.
- **Strict Role-Credential Matching**: The server rejects credential crossover attempts (e.g., logging in as Administrator with Tele-caller credentials).
- **Object-Level Authorization**: Tele-callers can only view and manage leads, calls, and follow-ups assigned directly to them.
- **Security Headers**: HSTS, X-Content-Type-Options: nosniff, and X-Frame-Options: DENY are configured in production settings.

---

## ⚠️ Known Limitations & Future Improvements

- **Export Record Caps**: PDF exports are capped at 200 records per document and Excel exports at 500 records per sheet to preserve server memory.
- **Future Improvements**:
  - WebRTC in-browser VoIP dialing integration (e.g. Twilio / Asterisk).
  - Automated WhatsApp/SMS callback reminders via webhook notifications.
  - Granular audit trail logging for administrative actions.
