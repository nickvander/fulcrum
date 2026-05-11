"""
Integration tests for the Safe Sync with Approval Workflow.

Tests the pending sync staging, approval, rejection, and change logging endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session
from src.models.pending_sync import PendingSyncChange, SyncBatch
from src.models.product import Product


pytestmark = pytest.mark.db


class TestPendingSyncFlow:
    """Tests for the pending sync workflow."""

    def test_sync_push_stages_changes(
        self, client: TestClient, admin_headers: dict, test_product: Product
    ):
        """Test that sync-push stages changes instead of applying directly."""
        response = client.post(
            "/api/v1/integrations/sheets/sync-push",
            headers=admin_headers,
            json={
                "entity": "products",
                "changes": [
                    {"id": test_product.id, "field": "cost_price", "new_value": "25.00"},
                    {"id": test_product.id, "field": "resale_price", "new_value": "50.00"},
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["staged_count"] == 2
        assert "batch_id" in data
        assert data["batch_id"] > 0
        assert "staged for review" in data["message"].lower()

    def test_pending_sync_count(
        self, client: TestClient, admin_headers: dict, staged_sync_batch: int
    ):
        """Test getting the pending sync count."""
        response = client.get(
            "/api/v1/integrations/sync/pending/count",
            headers=admin_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert data["count"] >= 2  # At least the 2 changes from fixture

    def test_list_pending_batches(
        self, client: TestClient, admin_headers: dict, staged_sync_batch: int
    ):
        """Test listing pending sync batches."""
        response = client.get(
            "/api/v1/integrations/sync/pending",
            headers=admin_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "batches" in data
        assert "total_pending" in data
        
        # Should have at least the staged batch
        assert data["total_pending"] > 0
        batch = data["batches"][0]
        assert "id" in batch
        assert "source" in batch
        assert "status" in batch
        assert "changes" in batch

    def test_list_pending_batches_query_count_stays_bounded(
        self,
        client: TestClient,
        admin_headers: dict,
        db: Session,
        test_admin_user,
        test_product: Product,
    ):
        """Listing pending batches should not query changes one batch at a time."""
        for batch_index in range(4):
            batch = SyncBatch(
                user_id=test_admin_user.id,
                source="google_sheets",
                status="pending",
                total_changes=2,
            )
            db.add(batch)
            db.flush()

            db.add_all(
                [
                    PendingSyncChange(
                        batch_id=batch.id,
                        entity="products",
                        entity_id=test_product.id,
                        entity_name=test_product.name,
                        entity_sku=test_product.sku,
                        field=f"field_{batch_index}_a",
                        old_value="old",
                        new_value="new",
                        status="pending",
                    ),
                    PendingSyncChange(
                        batch_id=batch.id,
                        entity="products",
                        entity_id=test_product.id,
                        entity_name=test_product.name,
                        entity_sku=test_product.sku,
                        field=f"field_{batch_index}_b",
                        old_value="old",
                        new_value="new",
                        status="pending",
                    ),
                ]
            )
        db.flush()

        statements = []

        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        event.listen(db.bind, "before_cursor_execute", before_cursor_execute)
        try:
            response = client.get("/api/v1/integrations/sync/pending", headers=admin_headers)
        finally:
            event.remove(db.bind, "before_cursor_execute", before_cursor_execute)

        assert response.status_code == 200
        assert response.json()["total_pending"] == 8
        assert len(statements) <= 4

    def test_approve_sync_changes(
        self, client: TestClient, admin_headers: dict, staged_sync_batch: int, db: Session
    ):
        """Test approving sync changes."""
        # Get the pending changes
        pending_response = client.get(
            "/api/v1/integrations/sync/pending",
            headers=admin_headers,
        )
        pending_data = pending_response.json()
        
        assert pending_data["total_pending"] > 0, "No pending changes to approve"
        
        batch = pending_data["batches"][0]
        change_ids = [c["id"] for c in batch["changes"][:1]]  # Approve first change
        
        response = client.post(
            "/api/v1/integrations/sync/approve",
            headers=admin_headers,
            json={
                "batch_id": batch["id"],
                "change_ids": change_ids,
                "action": "approve"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["applied_count"] >= 0

    def test_reject_sync_changes(
        self, client: TestClient, admin_headers: dict, staged_sync_batch: int
    ):
        """Test rejecting sync changes."""
        # Get the pending changes
        pending_response = client.get(
            "/api/v1/integrations/sync/pending",
            headers=admin_headers,
        )
        pending_data = pending_response.json()
        
        assert pending_data["total_pending"] > 0, "No pending changes to reject"
        
        batch = pending_data["batches"][0]
        change_ids = [c["id"] for c in batch["changes"]]
        
        response = client.post(
            "/api/v1/integrations/sync/approve",
            headers=admin_headers,
            json={
                "batch_id": batch["id"],
                "change_ids": change_ids,
                "action": "reject"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "rejected" in data["message"].lower()


class TestChangeLogs:
    """Tests for the change log functionality."""

    def test_list_change_logs(
        self, client: TestClient, admin_headers: dict
    ):
        """Test listing change logs."""
        response = client.get(
            "/api/v1/integrations/change-logs",
            headers=admin_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "total" in data

    def test_filter_change_logs_by_source(
        self, client: TestClient, admin_headers: dict
    ):
        """Test filtering change logs by source."""
        response = client.get(
            "/api/v1/integrations/change-logs",
            headers=admin_headers,
            params={"source": "sheets_import"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All entries should have source = sheets_import
        for entry in data["entries"]:
            assert entry["source"] == "sheets_import"

    def test_filter_change_logs_by_entity(
        self, client: TestClient, admin_headers: dict
    ):
        """Test filtering change logs by entity type."""
        response = client.get(
            "/api/v1/integrations/change-logs",
            headers=admin_headers,
            params={"entity_type": "product"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for entry in data["entries"]:
            assert entry["entity_type"] == "product"

    def test_change_logs_pagination(
        self, client: TestClient, admin_headers: dict
    ):
        """Test change logs pagination."""
        response = client.get(
            "/api/v1/integrations/change-logs",
            headers=admin_headers,
            params={"limit": 5, "offset": 0}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) <= 5


class TestDirectEditLogging:
    """Tests for direct edit change logging."""

    def test_product_update_logs_changes(
        self, client: TestClient, admin_headers: dict, test_product: Product
    ):
        """Test that updating a product creates change log entries."""
        old_name = test_product.name
        new_name = f"{old_name} (Updated)"
        
        # Update the product
        response = client.put(
            f"/api/v1/products/{test_product.id}",
            headers=admin_headers,
            json={"name": new_name}
        )
        
        assert response.status_code == 200
        
        # Check change logs
        logs_response = client.get(
            "/api/v1/integrations/change-logs",
            headers=admin_headers,
            params={"entity_id": test_product.id, "entity_type": "product"}
        )
        
        assert logs_response.status_code == 200
        logs_data = logs_response.json()
        
        # Should have at least one entry for the name change
        name_changes = [e for e in logs_data["entries"] if e["field"] == "name"]
        assert len(name_changes) > 0
        
        latest = name_changes[0]
        assert latest["source"] == "direct_edit"
        assert latest["new_value"] == new_name
