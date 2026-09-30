# CCM — Testing & Quality Assurance Guide

This document details the automated test suite, test structure, command execution, and manual QA checklists in **CCM (Campaign Call Manager)**.

---

## 1. Automated Test Suite Overview

CCM features a comprehensive automated test suite consisting of **57 unit and integration tests** spanning all major subsystems:

| Test Module | Test Class / Count | Focus Areas |
| :--- | :--- | :--- |
| `accounts/tests.py` | `AccountTests` (21 tests) | Authentication, role selection, role mismatch validation, password security, password reset tokens, tele-caller roster, deactivated account rejection, home page elements. |
| `analytics/tests.py` | `AnalyticsEngineTests`, `AnalyticsViewTests`, `ReportExportTests` (15 tests) | Analytics engine calculation correctness, date filters, KPI accuracy, outcome aggregations, PDF export generation, Excel export generation, record preview calculations. |
| `campaigns/tests.py` | `CampaignTests` (11 tests) | Campaign lifecycle, questionnaire building, question types, tele-caller assignment filtering, target progress calculations. |
| `customers/tests.py` | `CustomerTests` (5 tests) | Customer CRUD, search, filtering, CSV import row validation, duplicate phone checks. |
| `calls/tests.py` | `CallTests` (5 tests) | Live call recording, question response storage, callback scheduling, overdue detection, assignment status updates. |

---

## 2. Running Automated Tests

### Run the Complete Test Suite
```bash
python manage.py test
```

### Run Tests for a Specific Application
```bash
# Accounts & Authentication Tests
python manage.py test accounts

# Analytics & Reports Tests
python manage.py test analytics

# Campaigns & Questionnaire Tests
python manage.py test campaigns

# Customer & Import Tests
python manage.py test customers

# Calls & Follow-up Tests
python manage.py test calls
```

### Verbose Test Output
```bash
python manage.py test -v 2
```

---

## 3. Manual Regression & Quality Checklist

### Phase A: Public Landing & Theme
- [ ] Open `http://127.0.0.1:8000/` as an unauthenticated user.
- [ ] Verify the SaaS landing page renders with header, hero banner, metrics, and capabilities.
- [ ] Click **"Explore Capabilities"** and verify smooth scrolling to `#features`.
- [ ] Click the **Theme Toggle** (sun/moon icon). Confirm theme toggles between light and dark mode and persists upon page refresh.

### Phase B: Authentication & Role Matching
- [ ] Navigate to `/login/`. Confirm "Who are you?" role selection cards appear.
- [ ] Click **"Administrator"**. Enter tele-caller credentials (`ayush@gmail.com` / `12345`). Confirm server rejects login with: *"The selected role does not match this account. Please select the correct role."*
- [ ] Click **"Tele-caller"**. Enter admin credentials (`admin` / `admin123`). Confirm server rejects login with the same role mismatch error.
- [ ] Enter valid tele-caller credentials with "Tele-caller" role selected. Confirm successful login and redirection to Tele-caller Workspace (`/dashboard/`).
- [ ] Verify tele-caller sidebar shows only: *Dashboard, My Campaigns, My Customers, My Calls, My Follow-ups, Notifications*.
- [ ] Attempt manual direct URL entry to `/analytics/` or `/reports/`. Confirm **HTTP 403 Forbidden** page is displayed.
- [ ] Log out. Log in as `admin` / `admin123` with "Administrator" role selected. Confirm Admin Overview dashboard loads with full management sidebar.

### Phase C: Tele-caller Password Security Workflow
- [ ] As Admin, open `/tele-callers/`.
- [ ] Click a tele-caller to view profile details. Confirm Assigned Campaigns, Workload, Recent Calls, and Pending Follow-ups render without any `TypeError` queryset errors.
- [ ] Click **"Edit Account"**. Confirm there is **no password input field**.
- [ ] Click **"Reset Password"**. Confirm the confirmation screen appears showing the registered email.
- [ ] Click **"Dispatch Reset Link"**. Confirm flash notification indicates reset link was dispatched.
- [ ] In terminal (or configured email backend), locate the reset link: `http://127.0.0.1:8000/reset-password/<uidb64>/<token>/`.
- [ ] Open the reset link in an incognito window. Set a new password and confirm login works with the new password.

### Phase D: Responsive Layout & Browser Zoom
- [ ] Test layout at `100%`, `125%`, `150%`, and `200%` browser zoom. Confirm cards stack naturally without horizontal clipping.
- [ ] Open DevTools and switch to mobile viewport (iPhone 14 / 390px width).
- [ ] Confirm sidebar collapses into off-canvas drawer and hamburger button toggles navigation cleanly.
