# Audit Logs View Implementation

## Overview
Implemented a full Audit Logs View for administrators to track user actions and system events. This includes a backend API with filtering capabilities and a frontend UI with a searchable, paginated table.

## Changes

### Backend
- **Model**: Verified `UserAuditLog` model structure.
- **CRUD**: Updated `CRUDUserAuditLog` to support `start_date` and `end_date` filtering.
- **API**: Created `GET /api/v1/audit-logs` endpoint, accessible only to superusers.
    - Supports pagination (`skip`, `limit`).
    - Supports filtering by `user_id`, `action`, `start_date`, `end_date`.
- **Dependencies**: Added `get_current_active_superuser` dependency.
- **Tests**: Added `tests/test_audit_logs_api.py` covering superuser access, filtering, and permission checks.

### Frontend
- **Service**: Created `AuditLogService` to fetch logs from the API with filter parameters.
- **Component**: Created `AuditLogsComponent` (`admin/audit-logs`) displaying logs in a Material table.
    - Columns: ID, Action, User, Performed By, Details, Date.
    - Filters: Action, User ID, Date Range.
    - Pagination: Integrated `mat-paginator`.
- **Routing**: Added `/admin/audit-logs` route guarded by `AuthGuard`.
- **Navigation**: Added "Audit Logs" link to the Sidenav, visible only to admins.

## Verification Results

### Automated Tests
- **Backend**: `tests/test_audit_logs_api.py` passed.
    - Verified superuser access returns logs.
    - Verified normal user access is forbidden (403).
    - Verified filtering by action and date works correctly.
- **Frontend**: `audit-log.service.spec.ts` and `audit-logs.component.spec.ts` passed.

### Manual Verification Steps
1.  Log in as an Admin.
2.  Open the Sidenav and click "Audit Logs".
3.  Verify the table loads with audit log data.
4.  Enter an action (e.g., "update") and press Enter. Verify the list filters.
5.  Select a date range. Verify the list filters.
6.  Log in as a non-admin user. Try to access `/admin/audit-logs`. Verify access is denied (or redirected).
