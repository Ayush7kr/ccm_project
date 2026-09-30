# CCM — Functional Capabilities & Feature Documentation

This document provides a comprehensive overview of all functional modules and user workflows implemented in **CCM (Campaign Call Manager)**, complete with interface screenshots.

---

## 1. Public SaaS Landing Page (`/`)

- **Hero Banner**: High-impact SaaS introduction communicating value propositions with primary CTAs: *"Get Started"*, *"Explore Capabilities"*, and *"Sign In"*.
- **"Explore Capabilities"**: Smoothly scrolls to the interactive feature cards section (`#features`).
- **Capabilities Matrix**: 8 interactive cards detailing Campaign Management, Customer Directory, Live Calling Console, Questionnaires, Follow-up Tracking, Operational Analytics, Report Center, and Role-Based Access.
- **Workflow Steps**: Visual 3-step walkthrough: *1. Setup & Ingestion* ➔ *2. Targeted Calling & Logging* ➔ *3. Insights & Reporting*.
- **Role Breakdown**: Clear comparison cards for System Administrators vs Tele-callers.
- **Theme Switcher**: Instant light/dark mode toggling, persisted via `localStorage`.

![Public Landing Page](screenshots/landing_page.png)

---

## 2. Role-Selection & Authentication (`/login/`)

- **Interactive Role Choice**: "Who are you?" portal with dedicated cards for **Administrator** and **Tele-caller**.
- **Role-Aware Forms**: Switches cleanly between role cards and credential inputs without full-page reloads.
- **Strict Server Validation**: Prevents credential crossover attacks (e.g. attempting to log into Administrator portal with Tele-caller credentials).
- **Password Visibility**: Eye icon toggle to reveal/hide password input.
- **Remember Me**: Configures session expiry (browser session vs persistent session).
- **Navigation Controls**: Clean `← Back to Home` and `← Change Role` buttons.

![Role Selection and Login](screenshots/login_role_selection.png)

---

## 3. Administrator Dashboard (`/dashboard/`)

- **Real-Time KPI Cards**:
  - Total & Active Campaigns
  - Total Customer Directory Count
  - Calls Completed vs Calls Pending
  - Follow-ups Due & Overdue
- **Active Campaign Progress Tracker**: Visual progress bars showing target call completion percentages (capped at 100%).
- **Quick Action Bar**: Fast shortcuts to *Create Campaign*, *Import Leads*, *Assign Customers*, *Analytics*, and *Reports*.

![Admin Operations Dashboard](screenshots/admin_dashboard.png)

---

## 4. Tele-caller Personal Workspace (`/dashboard/`)

- **Personal Metrics**: Calls completed today, pending leads in queue, and follow-ups due today.
- **Next in Queue / Immediate Tasks**: Directly launches the Live Call Console for the agent's next assigned customer.
- **Assigned Campaigns**: View-only cards for active initiatives assigned to the tele-caller.

![Tele-caller Workspace](screenshots/telecaller_dashboard.png)

---

## 5. Campaign Management (`/campaigns/`)

- **Full Campaign CRUD**: Create, edit, toggle active/paused status, and delete campaigns.
- **Fields**: Name, description, campaign type, start date, end date, and target call volume.
- **Detailed Campaign Overview**: Real-time progress, enrolled customers list, assigned tele-callers, and call history.

---

## 6. Dynamic Questionnaire Builder (`/questionnaires/<campaign_id>/builder/`)

- **Campaign-Linked Questionnaires**: Attach bespoke surveys to specific campaigns.
- **5 Supported Question Types**:
  1. Single Choice (Radio)
  2. Multiple Choice (Checkboxes)
  3. Rating Scale (1 to 5 numeric stars)
  4. Open Ended (Text response)
  5. Yes / No (Binary option)
- **Live Preview Mode**: Verifies the exact survey layout agents see in the live call console.

---

## 7. Customer Directory & Bulk Import (`/customers/`)

- **Search & Filtering**: Instant search across customer name, phone, email, and company, with campaign and status filters.
- **CSV & Excel Import Engine**:
  - Ingests `.csv`, `.xlsx`, and `.xls` files.
  - Validates missing names, phone formats, and duplicate phone numbers within the file and against the existing database.
  - Interactive pre-import review table highlighting valid vs invalid rows.
  - Automatic enrollment into selected target campaigns.
- **Lead Assignment Engine (`/customers/assign/`)**:
  - Assign unassigned leads to specific tele-callers individually or in bulk.
  - Prevents double-assignment.

| Bulk Ingestion & Validation Preview | Lead Assignment to Tele-callers |
| :---: | :---: |
| ![Customer Import Engine](screenshots/customer_import.png) | ![Customer Lead Assignment](screenshots/customer_assign.png) |

---

## 8. Live Call Console (`/calls/record/<assignment_id>/`)

- **Tele-caller Calling Interface**:
  - Customer contact details, history of previous calls, and notes.
  - Live stopwatch timer tracking call duration in seconds.
  - Outcome selector: `Completed`, `No Answer`, `Unreachable`, `Busy`, `Follow-up Required`.
- **Dynamic Survey Injection**: When marked `Completed`, questions from the campaign's questionnaire render dynamically for response logging.
- **Instant Callback Scheduling**: Easily schedule follow-up date and time if callback is requested.
- **Post-Call Confirmation (`/calls/record/success/<call_id>/`)**: Direct buttons to proceed to the next customer in queue or return to the dashboard.

![Live Call Console and Questionnaire Logging](screenshots/telecaller_call_logging.png)

---

## 9. Follow-up & Callback Management (`/followups/`)

- **Automated Overdue Detection**: Background and on-demand detection converting pending follow-ups to `Overdue` once the scheduled date/time passes.
- **Task Management**: Mark follow-ups as `Completed` or `Cancelled`.
- **Data Isolation**: Tele-callers only see their own scheduled callbacks; administrators have organization-wide visibility.

![Follow-up Callback Queue](screenshots/followups_list.png)

---

## 10. Call Records & Activity Log (`/calls/records/`)

- **Organization-Wide & Agent Logs**: Complete log of all placed calls, outcomes, durations, and timestamps.
- **Outcome Status Indicators**: Color-coded badges for quick identification of conversion and callback requirements.

![Call History Records](screenshots/call_records.png)

---

## 11. Tele-caller Workforce Directory (`/telecallers/`)

- **Team Oversight**: Administrator portal listing all onboarded tele-callers, active status, call totals, and performance indicators.
- **Secure Password Reset**: Dedicated modal triggering cryptographic HMAC token resets without ever transmitting plain-text passwords.

![Tele-caller Management](screenshots/telecallers_management.png)

---

## 12. Analytics Engine & Report Center (`/analytics/` & `/reports/`)

- **Centralized Engine (`analytics/engine.py`)**:
  - Unified mathematical functions for KPIs, outcomes, trends, and agent comparisons.
  - Global date filters (`Today`, `Last 7 Days`, `Last 30 Days`, `This Month`, `Last Month`, `Custom`).
- **Interactive Visualizations**:
  - Call Outcome distribution chart (Chart.js donut).
  - Activity over time trend line (Chart.js multi-line).

![Analytics Dashboard](screenshots/analytics_dashboard.png)

- **Report Center**:
  - 5 customizable reports with real-time pre-export record count previews.
  - **PDF Export Engine**: Built with ReportLab, featuring corporate headers, metadata summaries, and alternating table rows.
  - **Excel Export Engine**: Built with `openpyxl`, featuring dark headers, bold metrics, and auto-adjusted column widths.

![Report Center and Export Configuration](screenshots/reports_center.png)

