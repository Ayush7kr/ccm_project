# Changelog

All notable changes to the **CCM (Campaign Call Manager)** project during this development, stabilization, and hardening pass are documented below.

---

## [Phase 10] — Responsive Zero-Scroll Data Tables & Creative UI Polish

### Table Responsiveness & Zero-Side-Scroll Architecture
- **Eliminated Horizontal Table Scrollbars**: Redesigned all primary data tables across the platform (`Follow-ups`, `Calls History`, `Customer Directory`, `Tele-callers Roster`, `Campaigns List`, and `Dashboards`) to fit completely on standard desktop viewports (1080p, 1366x768, 1280x800) without requiring horizontal scrolling.
- **Smart Text Truncation & Hover Tooltips**: Implemented `.cell-truncate`, `.cell-truncate-sm`, and `.cell-truncate-lg` utilities with single-line ellipsis and native tooltip attributes (`title="..."`) for long notes, customer names, and campaign titles.
- **Contextual Column Integration**: Merged secondary columns (e.g. Originating Call info directly below Campaign titles) to conserve horizontal real estate while enhancing context.
- **Responsive Viewport Column Adaptation**: Applied `.col-hide-xl`, `.col-hide-lg`, `.col-hide-md`, and `.col-hide-sm` breakpoints so secondary metadata hides gracefully on constrained viewports while preserving critical operational actions.
- **Contextual Action Dropdown Positioning**: Polished the Follow-up Action dropdown to open reliably directly below the trigger button within screen boundaries without clipping.
- **Zero Errors / Zero Regressions**: Ran the entire test suite (134 automated unit/integration tests) with 100% pass rate.

---

## [Phase 9] — Tele-caller Self-Registration, Interactive Landing Experience & Production Polish

### Tele-caller Self-Registration & Onboarding
- **Self-Registration Workflow (`/register/`)**: Created `telecaller_register` view in `accounts/views.py` allowing prospective tele-callers to register securely.
- **Strict Role Enforcement**: Enforces `role='TELE_CALLER'` exclusively to prevent privilege escalation.
- **Form Validations**: Validates username availability and regex formatting (`^[a-zA-Z0-9_.]+$`), required first/last names, unique valid email, phone number format, password length (minimum 6 characters), password confirmation match, and terms acceptance.
- **Secure Password Hashing**: Passwords are cryptographically hashed using Django's default PBKDF2 algorithm (`User.objects.create_user`).
- **Automated In-App Notifications**:
  - Tele-caller receives an immediate `Welcome to CCM!` notification on their workspace dashboard.
  - All active Administrators receive an alert notification: `New Tele-caller Registered` with contact details.
- **Automatic Login & Workspace Landing**: Newly registered callers are logged in immediately and redirected directly to their personalized `dashboard` queue.
- **Split-Screen Registration UI (`templates/auth/register.html`)**: Responsive two-column dark-mode layout matching the login aesthetic with interactive password visibility toggles and real-time validation alerts.
- **Seamless Cross-Navigation**: Added clear callout cards linking to registration from both Step 1 (Role Selection) and Step 2 (Credentials Form) in `templates/auth/login.html`.

### Interactive Home Page Experience (`templates/public/home.html`)
- **Simulated Calling Console Mockup**: Hero section features an interactive dialing console preview with live ticking call timer, animated audio wave equalizer, outcome status selectors, and an interactive survey star rating widget.
- **Interactive 4-Tab Platform Tour (`#showcase`)**: Added responsive tabbed showcase covering:
  1. *Precision Dialing & Stopwatch Logging*
  2. *Dynamic Questionnaire Engine & In-Call Capture*
  3. *Smart Callback Scheduler with Overdue Highlighting*
  4. *Audit-Grade Analytics & PDF/Excel Reports*
- **Interactive 5-Item FAQ Accordion (`#faq`)**: Added animated collapsible accordion answering common questions regarding tele-caller onboarding, survey questions, offline callbacks, and Excel/PDF reporting.
- **Hero & Navbar Polish**: Added dynamic tele-caller count to stats, prominent "Register as Tele-caller" CTAs, Lucide icon badges, and smooth scroll anchors.

### Comprehensive Test Suite & Stability
- Added 7 dedicated unit tests in `accounts/tests.py` covering anonymous access, authenticated redirection, validation error handling, password mismatch, duplicate credentials rejection, database storage, and notification delivery.
- All 134+ automated tests passing with 0 failures and 0 errors.

---

## [Phase 8] — Comprehensive Bug Audit, State-Action Consistency & Workflow Hardening

### Bug Fixes & State-Action Consistency
- **Admin Call Console 403 Link Elimination**: Resolved the "Template Action → Backend Rejection" issue on Admin pages. In `templates/campaigns/detail.html` (Enrolled Customers tab) and `templates/customers/detail.html`, replaced unconditional `record_call` links with role-aware and status-aware actions. Admins now see "View Customer" or assignment badges; only assigned tele-callers on active campaigns see "Call Console".
- **File Import Security & `.xls` Rejection**: Enforced a 10 MB maximum upload size limit in `customers/views.py`. Removed legacy `.xls` from the UI file picker and added an explicit rejection validation before `openpyxl` crashes with an `InvalidFileException`.
- **Campaign Target Calls Validation**: Added server-side validation rejecting negative target call inputs (`target_calls >= 0`) in `campaigns.views.campaign_edit`, matching `campaign_create`.
- **Follow-Up State Transition Hardening**: Hardened `calls/views.py` (`followup_complete` and `followup_cancel`) to reject requests targeting already completed or cancelled follow-ups. Added a new `followup_reschedule` workflow and modal, enabling overdue/pending callbacks to be rescheduled with a updated scheduled date/time.
- **Call Console Duration Boundary Validation**: Added an upper limit validation (`duration_sec <= 86400`) in `calls.views.record_call` preventing negative or unrealistic call lengths (>24 hours).
- **Report Center Filter Alignment**: Updated `analytics/engine.py` and `analytics/views.py` so telecaller filtering (`telecaller_id`) applies consistently across preview tables, PDF downloads, and Excel exports. Added automatic date range inversion correction (`date_from > date_to`).
- **Notification Smart Redirect Safeguard**: In `analytics/views.py` (`notification_read_single`), added verification that target campaigns and customers exist and that the current tele-caller is authorized before redirecting, eliminating 404/403 crashes on deleted entities.
- **Admin Dashboard Action Link Correction**: Linked the Action Required "Pending Calls" counter and KPI card directly to `/customers/?status=Assigned`.
- **Questionnaire Type Server-Side Validation**: Enforced strict validation of `question_type` against `Question.QUESTION_TYPES` in `campaigns/views.py`.
- **Campaign Deletion Impact Warning**: Enhanced `templates/campaigns/confirm_delete.html` and `campaigns/views.py` to calculate and display the number of historical calls and assignments that will be affected, with an explicit advisory recommending status archival (`Completed`/`Cancelled`) over hard deletion.
- **Follow-Up Action Column Redesign**: Replaced the separate side-by-side action buttons (`Mark Complete`, `Reschedule`, `Cancel`) with a compact, responsive `[ Actions ▾ ]` dropdown menu button in `templates/followups/list.html`. Built with viewport-aware fixed positioning to prevent table overflow clipping across all viewports (360px–1366px+) and zoom levels (80%–200%).
- **Follow-Up State-Aware Actions**: Active follow-ups (`Pending`, `Overdue`) render the action menu with `Mark Complete`, `Reschedule`, and `Cancel`. Completed and Cancelled follow-ups render clean, non-interactive badges (`✓ Completed`, `✕ Cancelled`) with no state-changing actions.
- **Follow-Up Quick Filter Pills**: Added instant status filter pills (`All`, `Pending`, `Overdue`, `Completed`, `Cancelled`) at the top of My Follow-ups, retaining historical follow-ups while allowing quick active queue filtering.
- **Duplicate Follow-up Prevention**: Hardened `calls/views.py:record_call` and `seed_data.py` to prevent duplicate active callbacks for the same customer at the exact same scheduled date and time by updating/re-associating the existing active callback instead of inserting redundant records.

### Testing & Verification
- Added 20 automated regression tests in `calls/tests_audit_hardening.py` covering follow-up state dropdown rendering, state-transition guards, RBAC/IDOR protection, and duplicate prevention.
- Total test suite expanded to **127 automated tests**, passing with 0 errors and 0 failures.

---

## [Phase 7] — Security Hardening, Decorator RBAC Strictness & Call Queue UX Alignment

### Security & RBAC
- **Strict `telecaller_required` Decorator**: Hardened `@telecaller_required` in [accounts/decorators.py](file:///f:/CCM/accounts/decorators.py) to strictly enforce `request.user.is_authenticated and request.user.is_telecaller_user`. Authenticated Admins attempting to access tele-caller-only workflows (such as `/calls/record/<id>/`) are now correctly blocked with HTTP 403 `PermissionDenied`.
- **Regression Security Suite**: Added [accounts/tests_security.py](file:///f:/CCM/accounts/tests_security.py) covering negative authorization across all user roles, admin isolation from tele-caller endpoints, and tele-caller isolation from management views.

### Call Queue & Assignment UX Alignment
- **Task Queue State Discrimination**: Overhauled task selection logic in [analytics/views.py](file:///f:/CCM/analytics/views.py). Tasks in the tele-caller dashboard are now explicitly tagged with `task_type` (`pending_call`, `in_progress_call`, `followup_task`).
- **Elimination of Invalid "Start Call" Actions**: Prevented completed customer assignments from rendering "Start Call" buttons that would trigger backend rejections.
- **Dedicated Follow-up Actions for Completed Assignments**: When a customer assignment is marked `Completed` but has a pending or overdue follow-up, the workspace presents an amber **"Handle Follow-up"** action linking directly to the follow-ups workflow instead of an invalid call initiation button.
- **Clean Task List Pruning**: Completed assignments without pending follow-ups are omitted from the active workspace queue.
- **KPI Semantic Clarification**:
  - Tele-caller dashboard KPI clarified to **"Pending Assignments"** to distinguish from total call outcomes.
  - Campaign detail page updated to clearly delineate **"Completed Calls"** (CallRecords count) and **"Pending Assignments"**, while introducing an explicit **"Call Records"** total counter.
- **Comprehensive Task Queue Test Suite**: Added [analytics/tests_task_queue.py](file:///f:/CCM/analytics/tests_task_queue.py) with 18 unit and integration tests covering assignment status lifecycle, task action rendering, campaign counter correctness, and sidebar RBAC.

---

## [Phase 6] — Production Stabilization, RBAC Hardening & Complete Documentation Pass

### Added
- **Public SaaS Landing Page (`/`)**: Added professional landing page with hero banner, 8 interactive capabilities cards, workflow overview, role comparison cards, and CTAs.
- **Interactive Role-Selection (`/login/`)**: Added dedicated role choice cards ("Administrator" vs "Tele-caller") preceding login credential entry.
- **Cryptographic Password Reset Engine**: Added `telecaller_reset_password` and `user_password_reset_confirm` views utilizing Django's `default_token_generator` and `urlsafe_base64_encode`.
- **Password Reset Templates**: Added `templates/telecallers/reset_password_confirm.html` and `templates/auth/password_reset_confirm.html`.
- **Custom Error Handlers**: Added `templates/errors/400.html` and configured `handler400`, `handler403`, `handler404`, and `handler500` in `config/urls.py`.
- **Responsive CSS Grid System**: Added 6 responsive CSS grid classes (`.responsive-grid-1-1`, `.responsive-grid-2-1`, `.responsive-grid-1-1-1`, etc.) to `main.css`.
- **Comprehensive Documentation Suite**: Added `docs/architecture.md`, `docs/setup.md`, `docs/authentication.md`, `docs/role-based-access.md`, `docs/database.md`, `docs/api.md`, `docs/features.md`, `docs/testing.md`, `docs/deployment.md`, `docs/troubleshooting.md`, and `docs/security.md`.

### Fixed
- **Tele-caller Detail Queryset Bug**: Fixed `TypeError: Cannot filter a query once a slice has been taken.` in `accounts.views.telecaller_detail` by ensuring all counts and filters are executed before applying slicing limits.
- **Role Elevation via Superuser Flag**: Fixed `is_admin_user` in `accounts.models.User` which previously returned `True` for tele-callers if `is_superuser` was set.
- **Deactivated User Handling**: Fixed login view to explicitly inform deactivated accounts that their access has been revoked rather than showing a generic credential failure.
- **Assigned Campaigns Display**: Fixed tele-caller detail page to display assigned campaigns and customer workload samples.

### Improved
- **Role-Based Sidebar Navigation**: Conditionally partitioned the sidebar so tele-callers only see operational items (*Dashboard, My Campaigns, My Customers, My Calls, My Follow-ups, Notifications*). Admin-only tools (*Tele-callers, Analytics, Reports*) are completely hidden.
- **Dark / Light Theme Persistence**: Synchronized theme switcher across landing, auth, dashboards, and error pages using `localStorage` (`ccm_theme`).
- **Responsive Tables**: Wrapped customer, call, campaign, and follow-up tables in `.table-responsive` containers to ensure clean horizontal scrolling on mobile viewports.
- **Zoom Compatibility**: Migrated fixed-width elements to fluid grid and flexbox layouts with relative units, supporting 80% to 200% browser zoom without clipping.

### Security
- **Eliminated Plaintext / Direct Password Editing**: Removed password fields from the tele-caller profile edit form; replaced with secure tokenized reset workflow.
- **Server-Side Role-Credential Matching**: Strictly validated selected role against authenticated user's role on the backend during `login_view`.
- **Protected Chart & Export APIs**: Added `@admin_required` to `/analytics/api/chart-data/` and all reporting export endpoints.
- **Object-Level Access Control**: Verified tele-caller ownership across lead details, live call console, and follow-up actions to prevent IDOR attacks.
- **Production Headers**: Hardened session cookies (`HttpOnly`, `SameSite=Lax`), CSRF cookies, and security headers in `config/settings.py`.

### Documentation
- Updated `README.md` with complete architecture overview, tech stack, quick start guide, testing instructions, and environment configurations.
- Created `.env.example` with safe placeholder configuration variables.
- Created `CONTRIBUTING.md` with development workflow and testing expectations.
