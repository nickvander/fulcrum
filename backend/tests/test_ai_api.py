"""
Tests for AI API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import io


@pytest.mark.db
def test_identify_product_endpoint(client: TestClient):
    """
    Test the AI product identification endpoint with file upload.
    """
    # Create a dummy image file
    dummy_image = io.BytesIO(b"fake image content")
    
    # Mock the orchestrator to avoid actual AI calls
    with patch('src.api.v1.endpoints.ai.AgentOrchestrator') as MockOrchestrator:
        mock_instance = MockOrchestrator.return_value
        mock_instance.process_product_image = AsyncMock(return_value={
            "name": "AI-Identified Widget",
            "description": "A high-quality widget identified from an image.",
            "sku": "AI-SKU-123",
            "brand": "TestBrand",
            "category": "Electronics"
        })
        
        response = client.post(
            "/api/v1/ai/identify-product",
            files={"file": ("test_image.jpg", dummy_image, "image/jpeg")}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "AI-Identified Widget"
        assert data["sku"] == "AI-SKU-123"


@pytest.mark.db
def test_identify_product_no_file(client: TestClient):
    """
    Test that the endpoint returns a validation error when no file is provided.
    """
    response = client.post("/api/v1/ai/identify-product")
    
    assert response.status_code == 422  # Unprocessable Entity - missing required file
