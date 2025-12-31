# Phase 11: Safe Sync with Approval Workflow

## Goal

Implement a staged sync workflow where changes from Google Sheets are **queued
for review** rather than applied immediately. This provides data integrity and
a full audit trail showing whether price changes came from Sheets or direct edits.

---

## Part 1: Backend Models & Migration ✅ COMPLETE

### Models Created

- **`SyncBatch`**: Tracks a batch of sync changes (lightweight history)
- **`PendingSyncChange`**: Individual pending changes, deleted after processing
- **`EntityChangeLog`**: Audit trail for all changes with source attribution

### Key Features

- `EntityChangeLog.source` distinguishes: `sheets_import`, `direct_edit`, `api`
- Automatic 30-day expiry on `SyncBatch` for history cleanup

---

## Part 2: Backend Endpoints ✅ COMPLETE

### Modified Endpoints

- **`POST /integrations/sheets/sync-push`**: Now stages changes instead of
  applying directly. Creates `SyncBatch` + `PendingSyncChange` records.

### New Endpoints

- **`GET /integrations/sync/pending`**: List pending batches with changes
- **`GET /integrations/sync/pending/count`**: Get count for badge display
- **`POST /integrations/sync/approve`**: Approve/reject selected changes
- **`GET /integrations/change-logs`**: View change history with filters

---

## Part 3: Apps Script Updates ✅ COMPLETE

- **Confirmation dialog** before pushing changes
- **Success dialog** directing user to Fulcrum to approve
- Updated messaging to reflect staged workflow

---

## Part 4: Frontend Components ✅ COMPLETE

### New Components

- **`PendingSyncDialog`**: Review pending changes with batch cards, diff
  preview, approve/reject actions
- **`ChangeLogDialog`**: View history with source filtering

### Settings Page Updates

- "Pending Sync Changes" section with badge count and Review button
- "Change Log" section with View Log button

---

## Part 5: Direct Edit Logging ✅ COMPLETE

- Product update endpoint now logs changes to `EntityChangeLog`
- Changes made directly in Fulcrum are logged with `source="direct_edit"`

---

## Part 6: Integration Tests ✅ COMPLETE

- `test_safe_sync.py` covers:
  - Sync push staging
  - Pending count and list
  - Approve/reject flow
  - Change log filtering
  - Direct edit logging

---

## Files Changed

### Backend

- `src/models/pending_sync.py` (NEW)
- `src/models/__init__.py` (updated)
- `src/api/v1/endpoints/integrations.py` (modified)
- `src/api/v1/endpoints/products.py` (modified)
- `src/services/change_log.py` (NEW)
- `alembic/versions/1b278953a6ce_add_sync_batch_and_change_log_tables.py` (NEW)

### Frontend

- `settings/components/pending-sync-dialog/` (NEW)
- `settings/components/change-log-dialog/` (NEW)
- `settings/components/settings/settings.ts` (modified)
- `settings/components/settings/settings.html` (modified)
- `settings/services/integrations.service.ts` (modified)

### Apps Script

- `scripts/google-sheets-addon/Code.gs` (modified)

---

## Verification Plan

### Automated Tests

```bash
docker compose exec backend python -m pytest tests/api/v1/test_safe_sync.py -v
```

### Manual Verification

1. Push changes from Google Sheets → Confirmation dialog appears
2. After push, changes appear in Settings → Integrations → Pending
3. Approve changes → Product prices update
4. Check Change Log → Approved changes show `source="sheets_import"`
5. Edit product directly in Fulcrum → Check Change Log shows `source="direct_edit"`
