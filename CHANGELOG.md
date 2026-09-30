# Changelog

All notable changes to the **CCM (Campaign Call Manager)** project during this development, stabilization, and hardening pass are documented below.

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
