# CCM — Security Architecture & Hardening Guide

This document describes the security controls, data protection mechanisms, authorization layers, and production hardening policies implemented in **CCM (Campaign Call Manager)**.

---

## 1. Security Architecture Summary

CCM employs defense-in-depth across the web application stack:

```text
Layer 1: Network / Transport  ──► HTTPS / TLS 1.3, HSTS Preload, Secure SSL Redirect
Layer 2: Browser Protections  ──► X-Frame-Options: DENY, X-Content-Type-Options: nosniff
Layer 3: Session & Cookies    ──► HttpOnly, SameSite=Lax, Secure Cookie Flags
Layer 4: Request Integrity    ──► Django CSRF Tokens enforced on all POST/PUT/DELETE
Layer 5: Authentication       ──► PBKDF2 Password Hashing, Strict Server-Side Role Matching
Layer 6: Authorization (RBAC) ──► @admin_required, Object-Level Assignment & IDOR Checks
Layer 7: Secret Management    ──► Zero Hardcoded Secrets; 100% Environment Configuration
```

---

## 2. Authentication & Credential Protection

### A. Password Hashing
- Passwords are encrypted using Django's default `PBKDF2SHA256` hasher with 870,000 hashing rounds.
- Plaintext passwords and hashes are never exposed through API responses, debug logs, or template contexts.

### B. Elimination of Direct Password Overwrites
- In previous versions, administrative profile editing forms contained direct password input fields. This created security vulnerabilities (accidental overwriting, unauthorized access without tele-caller knowledge).
- In the current architecture:
  - Direct password inputs are **completely removed** from profile edit forms.
  - Password recovery is handled via a dedicated cryptographic token workflow ([`accounts/views.py`](file:///f:/CCM/accounts/views.py#L294)).
  - Tokens use HMAC with salted hashes that automatically invalidate upon password alteration or after expiration.

### C. Strict Role-Credential Validation
- Attackers cannot select "Administrator" and authenticate with tele-caller credentials to elevate privileges.
- Validation is enforced on the server during `authenticate()`. Any mismatch terminates authentication and displays an error without logging in the user.

---

## 3. Session & Cookie Hardening

In [`config/settings.py`](file:///f:/CCM/config/settings.py):
```python
SESSION_COOKIE_HTTPONLY = True    # Prevents JavaScript theft of session cookies (XSS mitigation)
CSRF_COOKIE_HTTPONLY = False      # Allows CSRF protection across forms
SESSION_COOKIE_SAMESITE = 'Lax'   # Mitigates Cross-Site Request Forgery (CSRF)
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 86400        # Sessions expire after 24 hours

# Production Flags (when DEBUG=False):
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True      # Cookies sent over HTTPS only
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000    # Strict-Transport-Security (1 year)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = 'DENY'          # Clickjacking mitigation
SECURE_CONTENT_TYPE_NOSNIFF = True# MIME-type sniffing mitigation
```

---

## 4. Object-Level Access Control & IDOR Prevention

Insecure Direct Object Reference (IDOR) vulnerabilities are actively prevented by asserting assignment ownership across all private views:

1. **Customers**: Tele-callers can only view customers where `CampaignCustomer.assigned_telecaller == request.user`.
2. **Calls**: Tele-callers can only initiate calls and record responses for leads assigned to them.
3. **Follow-ups**: Tele-callers can only view, complete, or cancel follow-ups where `FollowUp.assigned_to == request.user`.
4. **Notifications**: Users can only query notifications where `Notification.recipient == request.user`.

---

## 5. Production Error Masking & Dual-State Information Isolation

Production environments running with `DEBUG = False` route all errors to custom, hardened error templates:
- `400 Bad Request` (`templates/errors/400.html`)
- `403 Forbidden` (`templates/errors/403.html`)
- `404 Not Found` (`templates/errors/404.html`)
- `500 Server Error` (`templates/errors/500.html`)

These views guarantee that stack traces, database schema definitions, internal file system paths, and server environment variables are never exposed to clients. 

Furthermore, error templates employ a **dual-state inheritance pattern**:
- **Authenticated Users**: Error cards render seamlessly inside the secure dashboard layout with contextual return actions (e.g. Return to Dashboard or Switch Account).
- **Anonymous Visitors**: Error cards render centered within the public authentication container with safe navigation links (Back to Home, Sign In), preventing blank-screen render failures while strictly preventing leakage of internal navigation elements.

---

## 6. Tele-caller Self-Registration Security Controls

The public tele-caller registration portal (`/register/`) includes explicit defense measures against unauthorized privilege elevation:

1. **Role Pinning**: The registration controller hardcodes `role='TELE_CALLER'` in the Python creation method. It never inspects form inputs for role assignment, preventing privilege escalation to `ADMIN`.
2. **Server-Side Validation**:
   - Username: Sanitized and restricted to `^[a-zA-Z0-9_.]+$`.
   - Email: Validated for RFC compliance and uniqueness.
   - Password: Minimum 6 characters with mandatory confirmation match.
   - Terms Acceptance: Explicit agreement flag required before user creation.
3. **Cryptographic Protection**: Passwords are saved exclusively through `create_user()`, ensuring PBKDF2 hashing with salt.

---

## 7. Historical Data Safety & Non-Destructive Archiving

To prevent permanent loss of historical reporting records and compliance data:

1. **Soft-Deletion Archive Pattern**:
   - When an administrator deletes a customer, the system evaluates relationship history (`call_records`, `follow_ups`, `campaign_links`).
   - If historical records exist, the customer is deactivated (`is_active = False`) and archived rather than executing an irreversible SQL `CASCADE DELETE`.
   - Call records, questionnaire responses, and callback audit trails remain intact for accurate analytics.
2. **Hard-Deletion Isolation**: Permanent database deletion is permitted only for newly created or uncontacted test leads with zero operational history.
3. **Reactivation Workflow**: Archived customer records can be restored by administrators at any time via a protected `@admin_required` POST endpoint (`/customers/<id>/restore/`).

