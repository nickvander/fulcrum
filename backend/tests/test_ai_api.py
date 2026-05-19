"""
Tests for AI API endpoints — covers the readiness gate that hides AI
features when StoreSettings.ai_enabled is off or no API key is configured.
"""
import io

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch


def _enable_ai(db) -> None:
    """Flip StoreSettings into the configured state used by the gating tests."""
    from src.core.encryption import encryption_service
    from src.crud.crud_store_settings import store_settings as crud_store_settings

    settings = crud_store_settings.get_settings(db)
    settings.ai_enabled = 1
    settings.ai_provider = "google"
    settings.ai_google_api_key = encryption_service.encrypt("fake-key-for-tests")
    db.add(settings)
    db.commit()


# ---------------------------------------------------------------------------
# Capabilities endpoint
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_capabilities_defaults_to_not_ready(client: TestClient):
    resp = client.get("/api/v1/ai/capabilities")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ready"] is False
    assert body["enabled"] is False
    assert body["configured"] is False
    assert body["provider"] == "google"


@pytest.mark.db
def test_capabilities_reports_ready_when_enabled_and_keyed(client: TestClient, db):
    _enable_ai(db)
    resp = client.get("/api/v1/ai/capabilities")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ready"] is True
    assert body["enabled"] is True
    assert body["configured"] is True


@pytest.mark.db
def test_capabilities_not_ready_when_enabled_but_no_key(client: TestClient, db):
    from src.crud.crud_store_settings import store_settings as crud_store_settings

    settings = crud_store_settings.get_settings(db)
    settings.ai_enabled = 1
    settings.ai_provider = "google"
    settings.ai_google_api_key = None
    db.add(settings)
    db.commit()

    resp = client.get("/api/v1/ai/capabilities")
    body = resp.json()
    assert body["ready"] is False
    assert body["enabled"] is True
    assert body["configured"] is False


# ---------------------------------------------------------------------------
# /identify-product gate
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_identify_product_rejected_when_ai_disabled(client: TestClient):
    dummy_image = io.BytesIO(b"fake image content")
    resp = client.post(
        "/api/v1/ai/identify-product",
        files={"file": ("test_image.jpg", dummy_image, "image/jpeg")},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "apiErrors.ai.disabled"


@pytest.mark.db
def test_identify_product_endpoint(client: TestClient, db):
    _enable_ai(db)
    dummy_image = io.BytesIO(b"fake image content")
    with patch("src.api.v1.endpoints.ai.AgentOrchestrator") as MockOrchestrator:
        mock_instance = MockOrchestrator.return_value
        mock_instance.process_product_image = AsyncMock(
            return_value={
                "name": "AI-Identified Widget",
                "description": "A high-quality widget identified from an image.",
                "sku": "AI-SKU-123",
                "brand": "TestBrand",
                "category": "Electronics",
            }
        )

        resp = client.post(
            "/api/v1/ai/identify-product",
            files={"file": ("test_image.jpg", dummy_image, "image/jpeg")},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "AI-Identified Widget"
        assert data["sku"] == "AI-SKU-123"


@pytest.mark.db
def test_identify_product_no_file(client: TestClient):
    resp = client.post("/api/v1/ai/identify-product")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /generate-description gate
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_generate_description_rejected_when_ai_disabled(client: TestClient):
    resp = client.post(
        "/api/v1/ai/generate-description",
        json={"product_name": "Anything"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "apiErrors.ai.disabled"


@pytest.mark.db
def test_generate_description_happy_path(client: TestClient, db):
    _enable_ai(db)
    with patch("src.api.v1.endpoints.ai.AgentOrchestrator") as MockOrchestrator:
        instance = MockOrchestrator.return_value
        instance.generate_product_description = AsyncMock(
            return_value={
                "description": "A great widget.",
                "seo_keywords": ["widget", "tool"],
                "tone_used": "Professional",
            }
        )

        resp = client.post(
            "/api/v1/ai/generate-description",
            json={"product_name": "Wonder Widget"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["description"] == "A great widget."
        assert body["seo_keywords"] == ["widget", "tool"]


# ---------------------------------------------------------------------------
# /generate-listing-description gate
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_generate_listing_description_rejected_when_ai_disabled(client: TestClient):
    resp = client.post(
        "/api/v1/ai/generate-listing-description",
        json={"product_id": 1, "marketplace_name": "amazon"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "apiErrors.ai.disabled"


@pytest.mark.db
def test_generate_listing_description_unknown_product(client: TestClient, db):
    """Even when AI is on, an unknown product returns the per-marketplace
    error envelope (200 with `error` field) — the gate is upstream of the
    product lookup, but a 200-with-error keeps the existing UI contract."""
    _enable_ai(db)
    resp = client.post(
        "/api/v1/ai/generate-listing-description",
        json={"product_id": 999_999, "marketplace_name": "amazon"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "not found" in (body.get("error") or "")
    assert body["marketplace"] == "amazon"


@pytest.mark.db
def test_generate_listing_description_happy_path(client: TestClient, db, test_product):
    _enable_ai(db)
    with patch("src.api.v1.endpoints.ai.AgentOrchestrator") as MockOrchestrator:
        instance = MockOrchestrator.return_value
        instance.generate_product_description = AsyncMock(
            return_value={
                "description": "Amazon-tuned blurb.",
                "seo_keywords": ["amazon", "widget"],
            }
        )

        resp = client.post(
            "/api/v1/ai/generate-listing-description",
            json={"product_id": test_product.id, "marketplace_name": "amazon"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["description"] == "Amazon-tuned blurb."
        assert body["marketplace"] == "amazon"
        assert body["keywords"] == ["amazon", "widget"]
