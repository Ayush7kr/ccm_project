# CCM — Local Setup & Installation Guide

This document provides step-by-step instructions to install, configure, seed, and run the **Campaign Call Manager (CCM)** platform locally.

---

## 1. System Prerequisites

Ensure you have the following installed on your machine:
- **Python**: Version `3.10`, `3.11`, or `3.12`
- **Git** (optional, for version control)
- **SQLite** (bundled with Python for local development) or **PostgreSQL 14+** (for production)
- Modern web browser (Chrome, Edge, Firefox, Safari)

---

## 2. Step-by-Step Installation

### Step 1: Navigate to Project Directory
```bash
cd f:/CCM
```

### Step 2: Create and Activate Virtual Environment
```bash
# Windows (PowerShell / Command Prompt)
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Required Dependencies
```bash
pip install -r requirements.txt
```

Verify installed packages:
```bash
pip list
```

---

## 3. Environment Configuration

Copy the sample environment file to create your local `.env`:
```bash
cp .env.example .env
```

Ensure `.env` contains safe local development defaults:
```env
# Django Core
SECRET_KEY=local-dev-insecure-secret-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (defaults to SQLite when DATABASE_URL is omitted)
# DATABASE_URL=postgresql://user:pass@localhost:5432/ccm_db

# Email Configuration (Console backend logs emails to terminal in dev)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=noreply@ccm.local

# Logging
LOG_LEVEL=INFO
DJANGO_LOG_LEVEL=INFO
```

---

## 4. Database Setup & Migrations

Apply existing Django database migrations:
```bash
python manage.py migrate
```

---

## 5. Seed Demonstration & Test Data

CCM includes a built-in management command to seed realistic campaign, tele-caller, customer, call record, and questionnaire data:

```bash
python manage.py seed_data
```

This command provisions:
- **1 Admin user**: `admin` (password: `admin123`)
- **4 Tele-callers**:
  - `ayush` (`ayush@gmail.com`, password: `12345`)
  - `telecaller1` (password: `password123`)
  - `telecaller2` (password: `password123`)
  - `telecaller3` (password: `password123`)
- **Active Campaigns**: e.g., *Customer Retention & Loyalty Drive*, *Q4 Enterprise Outreach*
- **Questionnaires**: With single-choice, multiple-choice, rating scale, and open-ended questions.
- **Customers**: Pre-enrolled and assigned to tele-callers.
- **Call Records & Follow-ups**: Realistic duration, outcomes, and scheduled callbacks.

---

## 6. Starting the Development Server

Launch Django's built-in development server:
```bash
python manage.py runserver 127.0.0.1:8000
```

Open your browser and navigate to:
```text
http://127.0.0.1:8000/
```

- **Root URL (`/`)**: Displays the Public SaaS Landing Page.
- **Sign In (`/login/`)**: Displays the Role Selection and Authentication Portal.
- **Health Check (`/health/`)**: Returns JSON health status of web server and database.

---

## 7. Running the Automated Test Suite

Run the full Django test suite to verify system integrity:
```bash
python manage.py test
```

Expected output:
```text
Ran 134 tests in ~210s
OK
```
