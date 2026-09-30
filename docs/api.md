# CCM — Application Endpoints & API Reference

This document describes the HTTP endpoints, APIs, and data export services provided by **CCM (Campaign Call Manager)**.

---

## 1. System & Health Endpoints

### `GET /health/`
- **Purpose**: Microservice and monitoring health check endpoint.
- **Authentication**: None required (public).
- **Responses**:
  - `200 OK`:
    ```json
    {
      "status": "healthy",
      "database": "connected"
    }
    ```
  - `503 Service Unavailable`:
    ```json
    {
      "status": "unhealthy",
      "database": "disconnected"
    }
    ```

---

## 2. Analytics & Charting API

### `GET /analytics/api/chart-data/`
- **Purpose**: Provides asynchronous JSON data feeds for Chart.js rendering on the Analytics dashboard.
- **Authentication**: Required (`ADMIN` role enforced via `@admin_required`).
- **Query Parameters**:
  - `campaign_id` *(optional)*: Integer PK of a specific campaign.
  - `date_range` *(optional)*: Preset string (`today`, `7days`, `30days`, `this_month`, `last_month`, `custom`).
  - `date_from` *(optional)*: Format `YYYY-MM-DD` (when `date_range=custom`).
  - `date_to` *(optional)*: Format `YYYY-MM-DD` (when `date_range=custom`).
- **Response `200 OK`**:
  ```json
  {
    "status_labels": ["Completed", "No Answer", "Unreachable", "Busy", "Follow-up Required"],
    "status_counts": [142, 28, 14, 9, 31],
    "activity_labels": ["Sep 23", "Sep 24", "Sep 25", "Sep 26", "Sep 27", "Sep 28", "Sep 29"],
    "activity_total": [24, 38, 45, 40, 52, 30, 22],
    "activity_completed": [18, 25, 33, 29, 39, 21, 15],
    "telecaller_labels": ["Ayush Sharma", "Rohan Verma", "Michael Chen"],
    "telecaller_completed": [68, 44, 30]
  }
  ```
- **Error Responses**:
  - `403 Forbidden`: When accessed by unauthenticated users or non-admin roles.

---

## 3. Report Generation & Export Endpoints

All export endpoints require `ADMIN` authentication (`@admin_required`).

### `GET /reports/download/pdf/`
- **Purpose**: Generates and downloads a branded PDF report.
- **Query Parameters**:
  - `report_type`: `campaign`, `calls`, `responses`, `telecaller`, `followups`.
  - `campaign`: Integer PK.
  - `telecaller`: Integer PK.
  - `call_status`: Status string filter.
  - `date_range`, `date_from`, `date_to`: Standard date filter parameters.
- **Response**:
  - Header: `Content-Type: application/pdf`
  - Header: `Content-Disposition: attachment; filename="ccm_<report_type>_report.pdf"`
  - Body: Binary stream generated via `ReportLab` (capped at 200 rows for memory protection).

### `GET /reports/download/excel/`
- **Purpose**: Generates and downloads a formatted Excel spreadsheet.
- **Query Parameters**: Same as PDF export.
- **Response**:
  - Header: `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
  - Header: `Content-Disposition: attachment; filename="ccm_<report_type>_export.xlsx"`
  - Body: Binary stream generated via `openpyxl` with styled headers and auto-adjusted column widths (capped at 500 rows).

---

## 4. Notification Management Endpoints

### `GET /notifications/`
- **Purpose**: Renders the notification center for the authenticated user.
- **Authentication**: Required (`@login_required`).

### `POST /notifications/read-all/`
- **Purpose**: Marks all unread notifications for the active user as read.
- **Authentication**: Required (`@login_required`).
- **Response**: `302 Redirect` back to `/notifications/`.

### `GET /notifications/<id>/read/`
- **Purpose**: Marks a specific notification as read and redirects intelligently to its associated entity (e.g. campaign, customer, or follow-up list).
- **Authentication**: Required (`@login_required` + recipient ownership check).
