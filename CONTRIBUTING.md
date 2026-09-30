# Contributing to CCM (Campaign Call Manager)

Thank you for your interest in contributing to **CCM**! This document provides guidelines, coding standards, and testing expectations for contributing to this repository.

---

## 1. Development Setup

1. **Clone the repository**:
   ```bash
   git clone <repository_url>
   cd CCM
   ```
2. **Setup virtual environment**:
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure environment**:
   ```bash
   cp .env.example .env
   ```
5. **Apply migrations and seed data**:
   ```bash
   python manage.py migrate
   python manage.py seed_data
   ```
6. **Start local development server**:
   ```bash
   python manage.py runserver
   ```

---

## 2. Code Organization & Architecture Rules

- **Modular Django Apps**:
  - `accounts`: User authentication, roles (`ADMIN`, `TELE_CALLER`), profile management.
  - `campaigns`: Campaign lifecycle, target tracking, questionnaire builder.
  - `customers`: Lead directory, CSV/Excel import, lead assignment.
  - `calls`: Live call console, duration logging, question responses, callbacks.
  - `analytics`: Centralized metrics engine (`analytics/engine.py`), report generation, notifications.
- **Single Source of Truth**: Never duplicate KPI, completion, or outcome calculations in views or templates. All business logic must utilize functions in `analytics/engine.py`.
- **Strict Role-Based Access Control**:
  - Administrative endpoints must be guarded with `@admin_required`.
  - Tele-caller endpoints must enforce object-level ownership checks (e.g. `assigned_telecaller == request.user`).
  - Never rely on frontend CSS hiding for security.

---

## 3. Coding Expectations & Design Principles

- **No Raw Django Forms**: Frontend forms are rendered using semantic, accessible HTML5 templates styled with design tokens in `static/css/main.css`.
- **Responsive Layout**: Use standard grid classes (`.responsive-grid-1-1`, `.responsive-grid-2-1`, `.responsive-grid-1-1-1`, etc.). All cards and form fields must stack to a single column on tablet/mobile screens (`≤768px`).
- **Zoom Compatibility**: Avoid hardcoded widths or fixed heights that clip content at 100% to 200% zoom.
- **Password Security**: Never expose passwords, hashes, or direct password override inputs in profile editing views. Use Django's tokenized reset mechanism.

---

## 4. Testing Expectations

All modifications must include automated tests or update existing tests. Before opening a Pull Request:

```bash
python manage.py test
```

- **All tests must pass** (zero failures, zero errors).
- Add regression tests for any bug fix to guarantee the issue cannot reoccur.
- Verify both `ADMIN` and `TELE_CALLER` roles when testing views.

---

## 5. Submitting Pull Requests & Reporting Bugs

1. **Branches**: Create feature branches from `main` (e.g. `feature/lead-scoring` or `fix/telecaller-slice-query`).
2. **Commits**: Write clear, descriptive commit messages.
3. **Bug Reports**:
   - Provide steps to reproduce the issue.
   - Include user role (`ADMIN` or `TELE_CALLER`).
   - Include any relevant terminal or browser console error logs.
