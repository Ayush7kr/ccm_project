# CCM — Campaign Call Manager: Comprehensive System & Architecture Documentation

---

## 📌 Executive Summary

**CCM (Campaign Call Manager)** is a modern, enterprise-ready tele-calling campaign and customer engagement platform built with **Python 3.12**, **Django 6.1**, **Vanilla CSS/JS design tokens**, **Chart.js**, **ReportLab**, and **openpyxl**.

The platform enables organizations to orchestrate structured calling initiatives, safely ingest and assign leads, conduct live calls with stopwatch timers, dynamically capture bespoke questionnaire responses, manage scheduled callback lifecycles, and extract audit-grade operational intelligence with multi-format PDF and Excel exports.

The codebase features **148 automated unit and integration tests** passing with **0 failures and 0 errors**, 100% system check compliance, strict Role-Based Access Control (RBAC), and robust historical data protection.

---

## 🏗️ 1. Architecture & Tech Stack

```
f:/CCM/
├── manage.py
├── requirements.txt         # Core dependencies: Django, ReportLab, openpyxl, WhiteNoise, python-dotenv
├── config/                  # Core project configuration
│   ├── settings.py          # Settings, WhiteNoise, CONN_MAX_AGE, RBAC session cookies
│   ├── urls.py              # Central routing dispatch with role-aware redirects
│   ├── wsgi.py & asgi.py
├── accounts/                # Custom User Model, Authentication & Tele-caller Roster
│   ├── models.py            # User (Role: ADMIN / TELE_CALLER, phone, metrics)
│   ├── views.py             # Login, Logout, Register (/register/), Tele-caller CRUD, Password Reset
│   ├── decorators.py        # @admin_required, @telecaller_required
│   ├── tests.py             # Authentication & workflow tests
│   └── tests_security.py    # Comprehensive RBAC & IDOR negative authorization tests
├── campaigns/               # Campaign Lifecycle & Dynamic Questionnaire Builder
│   ├── models.py            # Campaign, Questionnaire, Question
│   ├── views.py             # Campaign CRUD, Status Toggles, Survey Builder & Preview
│   └── tests.py             # Campaign & Questionnaire creation tests
├── customers/               # Customer Directory, CSV/Excel Importer & Archive Lifecycle
│   ├── models.py            # Customer (phone, whatsapp_number, notes, is_active), CampaignCustomer
│   ├── views.py             # Customer CRUD, Archive/Restore, Importer, Bulk Assignment Engine
│   └── tests.py             # Customer CRUD, WhatsApp, notes, archiving, restore, import tests
├── calls/                   # Live Call Console, Questionnaire Responses & Follow-ups
│   ├── models.py            # CallRecord (duration >= 0), QuestionResponse, FollowUp
│   ├── views.py             # record_call, call_list, followup_list/complete/cancel/reschedule
│   ├── tests.py             # Live calling, survey response, and callback tests
│   └── tests_audit_hardening.py # Audit hardening, action dropdowns, notification triggers
├── analytics/               # Dashboards, Central Engine, PDF/Excel Reporting & Notifications
│   ├── models.py            # Notification (user alert system)
│   ├── engine.py            # Single source of truth for all KPIs, trends, and rankings
│   ├── views.py             # Role-based dashboard dispatch, Chart API, PDF/Excel export
│   ├── urls.py
│   ├── tests.py             # Analytics engine & export tests
│   └── tests_task_queue.py  # Tele-caller task queue & KPI delineation tests
├── static/                  # Production Vanilla CSS/JS assets (served via WhiteNoise)
│   ├── css/main.css         # SaaS Design Tokens, Dark/Light Themes, Zero-Scroll Tables
│   └── js/main.js           # Interactive stopwatch timer, chart renderers, modals, dropdowns
├── docs/                    # Complete system documentation guides & screenshots
└── templates/               # Modular Django HTML5 templates
    ├── auth/                # Login, role selection, tele-caller registration (/register/)
    ├── dashboard/           # Admin Dashboard & Telecaller Dashboard
    ├── campaigns/           # Campaign lists, creation, editing, preview
    ├── questionnaires/      # Dynamic builder & telecaller preview
    ├── customers/           # Lead directory, detail, bulk assignment, CSV/XLSX import & preview
    ├── calls/               # Call list & live call recording console with stopwatch timer
    ├── followups/           # Follow-up tracker, scheduler & contextual action dropdowns
    ├── telecallers/         # Telecaller roster & performance detail
    ├── analytics/           # Deep-dive campaign & question response analytics
    ├── reports/             # PDF & Excel export control center
    ├── notifications/       # User notification inbox
    └── errors/              # Dual-state 400, 403, 404, 500 error views
```

### Technology Breakdown:
- **Backend Framework**: Python 3.12 / Django 6.1
- **Database Layer**: SQLite (development) / PostgreSQL (production via `DATABASE_URL` with `CONN_MAX_AGE` connection pooling)
- **Static Asset Delivery**: WhiteNoise (`CompressedManifestStaticFilesStorage`) with Gzip/Brotli compression and cache busting
- **Authentication & RBAC**: Custom Django `AbstractUser` with strict server-side Role-Based Access Control (`ADMIN` vs `TELE_CALLER`)
- **Frontend Architecture**: Clean HTML5 semantic layout, custom Vanilla CSS3 (Design Tokens, Dark/Light mode support, zero Tailwind dependencies), Lucide Icons
- **Data Visualizations**: Chart.js 4.x via asynchronous REST endpoint (`/analytics/api/chart-data/`)
- **Document Generation**:
  - **PDF Export**: ReportLab (`SimpleDocTemplate`, `TableStyle`, corporate headers, KPI summaries)
  - **Excel Export**: `openpyxl` (styled dark headers, bold metrics, auto-formatted column dimensions)

---

## 🔐 2. Role-Based Authentication & Access Control (RBAC)

### 2.1 Custom User Model (`accounts.User`)
- Extends `AbstractUser` with specialized fields:
  - `role`: Choices `ADMIN` (System Administrator) or `TELE_CALLER` (Agent/Tele-caller), default=`'TELE_CALLER'`
  - `phone`: Contact phone number
  - Helper properties: `is_admin_user` and `is_telecaller_user`

### 2.2 Dual-Persona Dynamic Dashboard Dispatch
- Route `/dashboard/` dispatches based on active user role:
  - **Admin Users** $\rightarrow$ `admin_dashboard`: System KPIs (Total & Active Campaigns, Customers, Calls Completed vs Pending Workload, Overdue Follow-ups), Chart.js outcome distribution, campaign progress bars, tele-caller performance comparison table.
  - **Tele-callers** $\rightarrow$ `telecaller_dashboard`: Personal assigned customer queue, daily calls completed, pending call tasks, personal overdue follow-up alerts, quick call buttons.

### 2.3 Tele-caller Self-Registration (`/register/`)
- Prospective tele-callers can self-register via a dedicated onboarding portal.
- **Strict Role Pinning**: Automatically and immutably assigns `role='TELE_CALLER'` in Python code. Role tampering via POST data is impossible.
- **Field Validations**: Enforces unique username with regex check (`^[a-zA-Z0-9_.]+$`), required first/last names, unique email, password length (≥ 6 characters), password confirmation match, and terms acceptance.
- **Secure Password Hashing**: Hashed using Django's standard PBKDF2 with SHA-256 algorithm.
- **Automated In-App Notifications**:
  - Welcomes the newly registered agent.
  - Alerts all active administrators of the new registration.
- **Immediate Workspace Access**: Logs the new user in and redirects directly to their personal workspace queue.

### 2.4 RBAC Route Protection Decorators
- Implemented `@admin_required`:
  - Enforces authentication (redirects to `/login/` with `next` param if anonymous).
  - Validates `user.is_admin_user`.
  - Raises standard `PermissionDenied` (HTTP 403) for tele-callers attempting to access administrator-only routes.
- Implemented `@telecaller_required`:
  - Protects tele-caller specific operations while maintaining data isolation.
- Applied across all administrative endpoints:
  - Tele-caller roster (`/tele-callers/*`)
  - Campaign creation and lifecycle management (`/campaigns/create/`, `/campaigns/<id>/edit/`, etc.)
  - Customer creation, edit, archiving, restore, import, and bulk assignment (`/customers/*`)
  - Analytics and exports (`/analytics/`, `/reports/`, `/reports/download/pdf/`, `/reports/download/excel/`)

### 2.5 Branded Dual-State HTTP Error Pages
Hardened error templates handle all HTTP exceptions gracefully:
- [400.html](file:///f:/CCM/templates/errors/400.html): Bad Request
- [403.html](file:///f:/CCM/templates/errors/403.html): Access Denied with clear explanation
- [404.html](file:///f:/CCM/templates/errors/404.html): Resource Not Found with breadcrumb navigation
- [500.html](file:///f:/CCM/templates/errors/500.html): Server Error handling with support links
- **Dual-State Inheritance**: Authenticated users see the error inside the application layout with return buttons; unauthenticated visitors receive a centered card without navigation leakage or blank screens.

---

## ⚙️ 3. Core Modules & Operational Features

### 📋 Module 1: Campaigns & Lifecycle Management
- **Campaign CRUD**: Creation, detailed viewing, updating, and status toggles (`Draft`, `Active`, `Paused`, `Completed`).
- **Target Tracking**: Configurable target call counts, date ranges, and completion percentage against recorded calls (capped at 100%).
- **Roster & Workload Stats**: Real-time aggregation of customers assigned, pending calls, and completed records.

### 📝 Module 2: Dynamic Questionnaire Builder & Preview Engine
- **Dynamic Form Builder**:
  - Administrators can build tailored call scripts per campaign.
  - Supports 5 distinct input types:
    1. `single_choice` — Radio button selections
    2. `multiple_choice` — Checkbox multi-select options
    3. `rating_scale` — 1 to 5 Star ratings
    4. `open_ended` — Multi-line text feedback
    5. `yes_no` — Binary toggle decisions
  - Client-side question ordering, option management, and required/optional toggles.
- **Tele-caller Live Preview**:
  - Interactive preview screen allowing admins and agents to test the survey layout before launching calls.

### 👥 Module 3: Customer Management, Omnichannel Contacts & Import Engine
- **Customer Directory**: Searchable, filterable list of leads with contact details, company, notes, campaign status, and activity status (`Active` vs `Archived`).
- **Omnichannel Contact Details**:
  - Primary contact `phone`.
  - Optional `whatsapp_number` with length validation (≥ 7 digits).
  - Direct WhatsApp chat link (`https://wa.me/...`) on detail and calling views.
  - Persistent customer profile `notes` card providing background context for agents before placing calls.
- **Historical Data Safety & Archive Lifecycle**:
  - Deleting a customer with existing calls, follow-ups, or campaign links deactivates and archives them (`is_active = False`) rather than executing a destructive cascade delete.
  - Permanent deletion is reserved strictly for test leads with zero historical activity.
  - Dedicated restore endpoint (`POST /customers/<id>/restore/`) allows administrators to reactivate archived leads.
  - Inactive customers are excluded from new campaign assignments.
- **Spreadsheet Ingestion Engine**:
  - Ingests both `.csv` and modern Excel `.xlsx` files with support for all fields (`name`, `phone`, `whatsapp_number`, `email`, `company`, `address`, `city`, `state`, `notes`).
  - Dual encoding handling: `utf-8-sig` with fallback to `latin-1`.
  - Floating-point phone/WhatsApp normalization (e.g. `9876543210.0` $\rightarrow$ `9876543210`).
  - Pre-import review table highlighting valid vs invalid rows.
  - Downloadable sample CSV template (`/customers/import/sample/`).
- **Bulk Lead Assignment Engine**:
  - Assigns unassigned active customers to tele-callers individually or in bulk.
  - Excludes archived leads and prevents double-assignment.

### 📞 Module 4: Tele-caller Live Call Console
- **Console Interface**:
  - Live client-side stopwatch timer (Start, Pause, Resume, Reset).
  - Displays primary phone, WhatsApp number, persistent customer profile notes, and past call history.
- **Call Outcome Logging**:
  - Standardized call outcomes: `Completed`, `No Answer`, `Unreachable`, `Busy`, `Follow-up Required`.
  - Dynamic rendering of campaign questionnaire questions upon `Completed` outcome.
  - Auto-advancement of assignment state: `Completed` marks assignment completed; other dispositions mark assignment in progress.
- **Questionnaire Response Capture**:
  - Stores answers in `QuestionResponse` linked to `CallRecord`.
  - Handles JSON list storage for multiple choice options and integers for rating scales.

### ⏰ Module 5: Follow-up Scheduling & Overdue Tracker
- **Zero-Scroll Data Table**: Compact layout with text truncation, hover tooltips, and contextual badges.
- **Contextual Action Dropdown**: Clean floating menu opening directly below trigger buttons within screen boundaries.
- **Automated Overdue Detection**: Background and on-demand detection converting pending follow-ups to `Overdue` once the scheduled date/time passes.
- **Task Management**:
  - **Mark Complete**: Resolves follow-up task. Re-completion is strictly blocked.
  - **Reschedule**: Updates scheduled date and time via modal.
  - **Cancel**: Cancels unnecessary callbacks with state transition validation.
- **Notification Auto-Clearing**: Automatically marks related unread follow-up notifications as read when the follow-up task is marked completed or cancelled.

### 📊 Module 6: Centralized Analytics Engine (`analytics/engine.py`)
- **Single Source of Truth**:
  - Centralized calculations for core KPIs: Total Calls, Completed Calls, Conversion Rate, and **Avg Call Duration** (formatted in mm:ss).
  - Global date filters (`Today`, `Last 7 Days`, `Last 30 Days`, `This Month`, `Last Month`, `Custom`).
- **Interactive Visualizations**:
  - Call outcome distribution (Donut chart).
  - Activity over time trend lines (Multi-line chart).
- **Report Center**:
  - 5 customizable business reports (Campaign Summary, Call Activity, Tele-caller Performance, Customer Response, Follow-up Schedule).
  - Real-time pre-export record count previews.
  - High-performance PDF generation via ReportLab.
  - Formatted Excel generation via `openpyxl`.

### 🔔 Module 7: Notification System
- **Campaign Milestone Alerts (70%)**: Automatically alerts administrators when a campaign reaches 70% completed calls, with duplicate alert suppression.
- **Inactive Tele-caller Alerts**: Detects active tele-callers with assigned leads who have logged no calls in 7+ days.
- **Follow-up Reminders**: Dispatches reminders upon callback scheduling and auto-clears them upon task completion.

---

## 🧪 4. Automated Test Suite & Quality Assurance

CCM features an exhaustive automated test suite consisting of **148 tests (0 failures, 0 errors)**:

```bash
python manage.py test
```

### Test Suite Breakdown:

| Test Module | Tests | Focus Areas |
| :--- | :---: | :--- |
| `accounts/tests.py` | 28 | Authentication, role selection, role mismatch validation, password security, token reset, tele-caller roster, deactivated account rejection, home page elements, tele-caller self-registration workflow, field validations, in-app notifications. |
| `accounts/tests_security.py` | 31 | Strict RBAC decorator enforcement (`@admin_required`, `@telecaller_required`), negative authorization on all administrative URLs, tele-caller IDOR isolation, cross-role boundary enforcement. |
| `analytics/tests.py` | 15 | Centralized analytics engine calculation correctness, date filters, KPI accuracy (Avg Call Duration), outcome aggregations, PDF export generation, Excel export generation, record preview calculations. |
| `analytics/tests_task_queue.py` | 18 | Tele-caller task queue state discrimination, "Start Call" vs "Handle Follow-up" rendering, assignment status transitions, campaign KPI delineation. |
| `campaigns/tests.py` | 11 | Campaign lifecycle, questionnaire building, question types, tele-caller assignment filtering, target progress calculations. |
| `customers/tests.py` | 13 | Customer CRUD, search, activity filtering (`active`/`archived`), optional WhatsApp number validation, profile notes, archive/deactivation on delete with history, hard delete without history, customer restore, assignment lead filtering, CSV/XLSX import with WhatsApp and notes. |
| `calls/tests.py` | 9 | Live call recording, question response storage, callback scheduling, overdue detection, assignment status updates. |
| `calls/tests_audit_hardening.py` | 23 | Admin call console 403 prevention, follow-up action dropdowns, follow-up re-completion/cancellation rejection, follow-up rescheduling, duration bounds, file size limits, .xls rejection, questionnaire type validation, report filter alignment, duplicate follow-up prevention, campaign milestone (70%) alert triggers, notification auto-clearing, inactive tele-caller alerts. |
| **Total Test Suite** | **148** | **100% Pass Rate (0 failures, 0 errors)** |

---

## 🚀 5. Local Setup & Quick Start

### 5.1 Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- Virtual environment (`venv`)

### 5.2 Installation & Seeding
```bash
# 1. Activate virtual environment (Windows PowerShell)
.\venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Apply database migrations
python manage.py migrate

# 4. Populate demo data (campaigns, customers, questions, tele-callers)
python manage.py seed_data

# 5. Run automated tests
python manage.py test

# 6. Start development server
python manage.py runserver 127.0.0.1:8000
```

### 5.3 Default Demo Credentials

| Role | Username | Password | Access Rights & Privileges |
|---|---|---|---|
| **Administrator** | `admin` | `admin123` | Full access: Campaigns, Telecallers, Customers, Bulk CSV Import, Analytics, PDF/Excel Reports |
| **Tele-caller** | `ayush` | `12345` | Assigned campaigns, Customer call queue, Live call timer, Survey logging, Follow-up scheduler |
| **Tele-caller 1** | `telecaller1` | `password123` | Assigned campaigns, Customer call queue, Live call timer, Survey logging, Follow-up scheduler |
| **Tele-caller 2** | `telecaller2` | `password123` | Assigned campaigns, Customer call queue, Live call timer, Survey logging, Follow-up scheduler |
| **Tele-caller 3** | `telecaller3` | `password123` | Assigned campaigns, Customer call queue, Live call timer, Survey logging, Follow-up scheduler |

---

## 📈 6. Complete Deliverables Checklist

- ✅ **Complete Role-Based Access Control (RBAC)** across views, templates, navigation, and API endpoints.
- ✅ **Tele-caller Self-Registration Portal (`/register/`)** with strict role-pinning, server validation, and dual notification alerts.
- ✅ **Omnichannel Contact Details**: Support for primary phone and optional WhatsApp number with direct chat links.
- ✅ **Persistent Customer Profile Notes**: Dedicated notes card accessible to tele-callers prior to and during calls.
- ✅ **Historical Data Integrity Safeguard**: Non-destructive archiving (`is_active = False`) and one-click restore endpoint.
- ✅ **Dynamic Questionnaire Builder** with 5 question types and live preview.
- ✅ **CSV / XLSX Import Engine** with column verification, phone normalization, and duplicate detection.
- ✅ **Interactive Tele-caller Console** with live stopwatch timer, disposition logging, and dynamic survey responses.
- ✅ **Automated Follow-up Lifecycle** with overdue status detection and contextual action dropdowns.
- ✅ **Automated Notification Lifecycle**: 70% campaign milestone alerts, inactive tele-caller detection, and auto-clearing on task resolution.
- ✅ **Executive Dashboards & Centralized Analytics Engine (`analytics/engine.py`)** with unified "Avg Call Duration" metric.
- ✅ **Report Center** with 5 reports and multi-format PDF and Excel exports.
- ✅ **Production Static Asset Delivery** via WhiteNoise with compression and persistent caching.
- ✅ **System Health Check Endpoint (`/health/`)** verifying web server and database connectivity.
- ✅ **148 / 148 Passing Unit & Integration Tests (100% OK)** with zero database resets or data loss.
- ✅ **Comprehensive Error Handling** (400, 403, 404, 500) with dual-state layout inheritance.
