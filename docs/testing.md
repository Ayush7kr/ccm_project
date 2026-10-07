# CCM — Testing & Quality Assurance Guide

This document details the automated test suite, test structure, command execution, and manual QA checklists in **CCM (Campaign Call Manager)**.

---

## 1. Automated Test Suite Overview

CCM features a comprehensive automated test suite consisting of **182 unit and integration tests** (0 failures, 0 errors) spanning all major subsystems:

| Test Module | Test Class / Count | Focus Areas |
| :--- | :--- | :--- |
| `accounts/tests.py` | `AccountTests` (28 tests) | Authentication, role selection, role mismatch validation, password security, password reset tokens, tele-caller roster, deactivated account rejection, home page elements, tele-caller self-registration workflow, field validations, and in-app notifications. |
| `accounts/tests_security.py` | `SecurityTests` (31 tests) | RBAC decorator enforcement (`@admin_required`, `@telecaller_required`), negative authorization, tele-caller IDOR isolation, and cross-role boundary enforcement. |
| `accounts/test_help_center.py` | `HelpCenterTests` (13 tests) | Role-based Help Center & FAQ: Anonymous 302 login redirects, Admin 200 OK access, Tele-caller 200 OK access, Admin category coverage (7 categories + General), Tele-caller category coverage (7 categories + General), strict server-side role isolation (tele-callers never receive Admin operational categories/text), General category sharing, helper unit tests (`get_faqs_for_user`), client search and accordion attributes, top navbar button (`#helpBtn`), and contextual FAQ deep-links on Customer Assignment and Follow-ups pages. |
| `analytics/tests.py` | `AnalyticsEngineTests`, `AnalyticsViewTests`, `ReportExportTests` (15 tests) | Analytics engine calculation correctness, date filters, KPI accuracy, outcome aggregations, PDF export generation, Excel export generation, record preview calculations. |
| `analytics/tests_task_queue.py` | `TaskQueueAndStatusTests` (18 tests) | Tele-caller task queue state discrimination, "Start Call" vs "Handle Follow-up" rendering, assignment status transitions, and campaign KPI delineation. |
| `campaigns/tests.py` | `CampaignTests` (11 tests) | Campaign lifecycle, questionnaire building, question types, tele-caller assignment filtering, target progress calculations. |
| `customers/tests.py` | `CustomerTests` (13 tests) | Customer CRUD, search, activity filtering (`active`/`archived`), optional WhatsApp number validation, profile notes, archive/deactivation on delete with history, hard delete without history, customer restore, assignment lead filtering, and CSV/XLSX import with WhatsApp and notes. |
| `customers/test_mentor_feedback.py` | `MentorFeedbackAssignmentTests`, `MentorFeedbackQuestionnaireTests` (21 tests) | Mentor feedback verification: Total/assigned/remaining counts (20 total, 16 assigned, 4 remaining), strict unassigned selection, already-assigned rejection, admin shift customer between tele-callers, tele-caller shift prohibition (403), inactive telecaller shift rejection, same-telecaller shift rejection, historical call ownership preservation (`CallRecord.telecaller`), live Call Console questionnaire display, all 5 question types (single, multi, rating, open, yes/no), server-side required question enforcement, response isolation, duplicate response prevention, and full call workflow integrity. |
| `calls/tests.py` | `CallTests` (9 tests) | Live call recording, question response storage, callback scheduling, overdue detection, assignment status updates. |
| `calls/tests_audit_hardening.py` | `AuditHardeningTests` (23 tests) | Admin call console 403 prevention, follow-up state/action matrix dropdowns, follow-up re-completion and cancellation rejection, follow-up rescheduling, duration bounds, file size limits, .xls rejection, questionnaire type validation, report filter alignment, duplicate follow-up prevention, campaign milestone (70%) alert triggers, notification auto-clearing, and inactive tele-caller alerts. |

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

### Phase E: Role-Based Help Center & FAQs (`/help/`)
- [ ] As an anonymous user, try visiting `http://127.0.0.1:8000/help/`. Confirm redirection to `/login/?next=/help/`.
- [ ] Log in as Administrator. Click the `?` Help icon button (`#helpBtn`) in the top navigation bar. Confirm Help Center opens with "Role: Administrator" badge and 28 answers.
- [ ] Search "campaign", "questionnaire", "shift", and "report". Verify matching questions highlight and auto-expand without page reloads.
- [ ] Search a non-existent keyword (e.g. "xyz123"). Confirm "No matching FAQs found" empty state appears. Click "Clear Search & View All" to restore list.
- [ ] Log out and log in as Tele-caller. Open Help Center. Confirm "Role: Tele-caller" badge is displayed.
- [ ] Confirm Admin-only categories (Campaign Management, Customer Management, Tele-caller Management, Reports) are NOT visible.
- [ ] Confirm Tele-caller categories (Call Console stopwatch, Questionnaires, Follow-ups, Call History privacy) are visible and functional.
- [ ] Navigate to Customer Assignment page, Call Console, and Follow-ups page. Verify contextual Help links jump smoothly to their respective FAQ anchors.

