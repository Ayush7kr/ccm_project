# CCM — Troubleshooting & FAQ Guide

This document catalogs common issues, causes, and solutions encountered during development, testing, and deployment of **CCM (Campaign Call Manager)**.

---

## 1. Authentication & Role Issues

### Issue: "The selected role does not match this account. Please select the correct role."
- **Cause**: The user selected "Administrator" on the login screen, but their database account has `role='TELE_CALLER'` (or vice-versa).
- **Solution**:
  - Click **"Change Role"** on the login card and select the matching role.
  - To inspect or modify a user's role in the database:
    ```bash
    python manage.py shell -c "from accounts.models import User; u = User.objects.get(username='myuser'); print(u.role)"
    ```

### Issue: "Your account has been deactivated. Please contact an administrator."
- **Cause**: The account has `is_active=False` in the database.
- **Solution**: An administrator must reactivate the account via `/tele-callers/<id>/edit/` by checking the **Account Active Status** checkbox.

---

## 2. Tele-caller Detail & Queryset Errors

### Issue: "TypeError: Cannot filter a query once a slice has been taken."
- **Cause**: Occurred historically when a queryset was limited/sliced (`queryset[:10]`) before a subsequent `.filter()` or `.count()` was executed.
- **Solution**:
  - In [`accounts/views.py`](file:///f:/CCM/accounts/views.py#L225), all aggregates, counts, and filters on `CampaignCustomer` and `CallRecord` are computed first. Slicing is applied only at the very end when binding objects to template context.

---

## 3. Database & Migration Issues

### Issue: "django.db.utils.OperationalError: no such table: ..."
- **Cause**: Migrations have not been applied to the local database.
- **Solution**:
  ```bash
  python manage.py migrate
  ```

### Issue: "Database connection failed in /health/"
- **Cause**: `DATABASE_URL` is pointing to an unreachable PostgreSQL host or incorrect credentials.
- **Solution**:
  - Verify PostgreSQL service is active: `sudo systemctl status postgresql`.
  - Check `.env` database parameters or unset `DATABASE_URL` to fallback to SQLite for local development.

---

## 4. Static Files & Styling Issues

### Issue: CSS styles or icons fail to load in production
- **Cause**: Static files have not been gathered into `STATIC_ROOT`, or Nginx is not pointing to `staticfiles/`.
- **Solution**:
  ```bash
  python manage.py collectstatic --noinput
  ```
  Ensure Nginx `location /static/` directive points directly to the `STATIC_ROOT` folder.

### Issue: Dark mode doesn't persist across page reloads
- **Cause**: Browser localStorage permissions disabled or cleared.
- **Solution**:
  - Verify `localStorage.getItem('ccm_theme')` in browser DevTools Console.
  - CCM's inline JavaScript automatically reads `ccm_theme` before page paint to prevent theme flashing.

---

## 5. CSV/Excel Lead Import Issues

### Issue: "Duplicate phone number in file" or "Phone number already registered"
- **Cause**: The CSV/Excel file contains multiple rows with the same phone number, or the phone number already exists in the `Customer` table.
- **Solution**:
  - CCM enforces unique phone numbers for lead deduplication. Check the preview table on `/customers/import/` which marks duplicates in red and allows skipping duplicate rows.
