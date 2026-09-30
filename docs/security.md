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

## 5. Production Error Masking

Production environments running with `DEBUG = False` route all errors to custom, branded error templates:
- `400 Bad Request` (`templates/errors/400.html`)
- `403 Forbidden` (`templates/errors/403.html`)
- `404 Not Found` (`templates/errors/404.html`)
- `500 Server Error` (`templates/errors/500.html`)

These views guarantee that stack traces, database schema definitions, internal file system paths, and server environment variables are never exposed to clients.
