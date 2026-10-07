# CCM — System Architecture Documentation

## 1. Overview & Architectural Principles

**CCM (Campaign Call Manager)** is a centralized SaaS platform built on **Django** (Python 3.12) designed for managing tele-calling campaigns, customer engagement, dynamic questionnaires, and real-time operational reporting.

The application follows clean architectural boundaries:
- **Separation of Concerns**: Modular Django applications partitioned by domain: `accounts`, `campaigns`, `customers`, `calls`, and `analytics`.
- **Single Source of Truth**: All operational metrics, completion rates, outcome counts, and performance rankings are computed by a centralized analytics engine (`analytics/engine.py`), preventing discrepancies across views and exports.
- **Strict Server-Side RBAC**: Role restrictions and object-level ownership checks are enforced at the view and database query level, never relying solely on UI visibility.

---

## 2. High-Level System Architecture Diagram

```mermaid
flowchart TD
    Client["Web Client (Desktop, Tablet, Mobile)"]
    Proxy["Nginx / Reverse Proxy (SSL/TLS)"]
    WSGI["Gunicorn WSGI Application Server"]
    
    subgraph DjangoApplication ["CCM Django Core Application"]
        Router["URL Dispatcher (config/urls.py)"]
        AuthMid["Authentication & Session Middleware"]
        RBAC["RBAC Decorators (@admin_required, @login_required)"]
        
        subgraph Apps ["Domain Modules"]
            AccountsApp["accounts (User, Roles, Password Reset)"]
            CampaignsApp["campaigns (Campaign, Questionnaire, Question)"]
            CustomersApp["customers (Customer, CampaignCustomer, Import)"]
            CallsApp["calls (CallRecord, QuestionResponse, FollowUp)"]
            AnalyticsApp["analytics (Engine, Reports, Notifications)"]
        end
        
        Engine["Analytics Engine (analytics/engine.py)"]
    end
    
    subgraph Storage ["Data & Storage Layer"]
        DB[(PostgreSQL / SQLite Database)]
        WhiteNoise["WhiteNoise Static Asset Pipeline (CompressedManifest)"]
        MediaFiles["Uploaded Assets / Exports"]
    end

    Client <--> Proxy
    Proxy <--> WSGI
    WSGI <--> Router
    Router --> AuthMid --> RBAC
    RBAC --> AccountsApp
    RBAC --> CampaignsApp
    RBAC --> CustomersApp
    RBAC --> CallsApp
    RBAC --> AnalyticsApp
    AnalyticsApp --> Engine
    Apps <--> DB
    WSGI <--> WhiteNoise
```

---

## 3. Django Applications & Responsibilities

| Application | Core Models | Primary Responsibilities |
| :--- | :--- | :--- |
| `accounts` | `User` | Custom user model inheriting from `AbstractUser`; role management (`ADMIN`, `TELE_CALLER`); role-aware login with server-side validation; cryptographic password reset workflows; tele-caller self-registration (`/register/`) with strict role-pinning and account provisioning; role-based Help Center & FAQ knowledge base (`accounts/faq_data.py`). |
| `campaigns` | `Campaign`, `Questionnaire`, `Question` | Campaign lifecycle management (Draft, Active, Paused, Completed, Archived); dynamic questionnaire builder supporting 5 question types. |
| `customers` | `Customer`, `CampaignCustomer` | Central customer directory; omnichannel contacts (phone, WhatsApp number, persistent profile notes); historical data protection with archiving lifecycle (`is_active`) and one-click restore; lead enrollment into campaigns; customer workload shifting (`/customers/shift/`); CSV/XLSX bulk lead import with row-level validation; assignment of leads to tele-callers. |
| `calls` | `CallRecord`, `QuestionResponse`, `FollowUp` | Live tele-caller dialing console; call status capture; question response recording; callback/follow-up scheduling and overdue detection; 70% campaign milestone detection; follow-up notification auto-clearing; inactive tele-caller alerts. |
| `analytics` | `Notification` | Centralized analytics engine (`analytics/engine.py`) calculating core KPIs (Total Calls, Completed Calls, Conversion Rate, Avg Call Duration); date-range and campaign filtering; Report Center with PDF (`ReportLab`) and Excel (`openpyxl`) export engines; notification center. |

---

## 4. End-to-End Request & User Workflow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Router as URL Dispatcher
    participant Auth as Auth & Role Validator
    participant View as View Layer
    participant Engine as Analytics Engine
    participant DB as Database

    User->>Router: GET / (Public Home)
    Router->>View: home_view()
    View->>DB: Fetch public aggregates
    View-->>User: Renders SaaS Landing Page

    User->>Router: POST /login/ (Role + Credentials)
    Router->>Auth: authenticate() + Strict Role Match
    Auth->>DB: Verify credentials and role
    alt Role Mismatch
        Auth-->>User: 200 OK (Role mismatch error)
    else Valid Credentials
        Auth-->>User: 302 Redirect -> /dashboard/
    end

    User->>Router: GET /dashboard/
    Router->>View: dashboard()
    alt user.role == 'ADMIN'
        View->>Engine: compute_call_kpis(), compute_call_outcome_counts()
        Engine->>DB: Query calls, campaigns, telecallers
        View-->>User: Admin Overview Dashboard
    else user.role == 'TELE_CALLER'
        View->>DB: Query assigned leads, upcoming follow-ups
        View-->>User: Tele-caller Personal Workspace
    end
```

---

## 5. Frontend & UI Architecture

1. **Design Tokens (`static/css/main.css`)**:
   - Central CSS custom property palette defining semantic colors (`--primary`, `--success`, `--warning`, `--danger`, `--bg-primary`, `--bg-secondary`, `--text-main`, `--text-muted`).
   - Standardized spacing, border radii, and box shadows.
2. **Light / Dark Mode**:
   - Implemented via `[data-theme="light"]` and `[data-theme="dark"]` CSS attributes.
   - Synchronized across the entire application and persisted in browser `localStorage` (`ccm_theme`).
3. **Responsive Grid Framework**:
   - Dedicated layout utilities: `.responsive-grid-1-1`, `.responsive-grid-2-1`, `.responsive-grid-1-1-1`, `.responsive-grid-4`.
   - Automatic single-column collapsing on tablet and mobile viewports (`≤768px`).
4. **Mobile Navigation**:
   - Desktop: Persistent, fixed-width sidebar with active state tracking.
   - Mobile (`≤768px`): Off-canvas navigation drawer triggered via hamburger button with background backdrop and outside-click dismissal.
