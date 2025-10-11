import pytest
from fastapi.testclient import TestClient

@pytest.mark.db
def test_identify_from_image(client: TestClient):
    """
    Test the AI image identification endpoint.
    This test relies on the DummyAIService to return a predictable mock response.
    """
    # The URL is valid but won't be fetched by the dummy service.
    image_url = "http://example.com/test_image.jpg"
    
    response = client.post(
        "/api/v1/ai/identify-from-image",
        json={"image_url": image_url},
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check that the response matches the mock data from DummyAIService
    assert data["name"] == "AI-Identified Widget"
    assert data["description"] == "A high-quality widget identified from an image."
    assert data["sku"] == "AI-SKU-123"

@pytest.mark.db
def test_identify_from_image_invalid_url(client: TestClient):
    """
    Test that the endpoint returns a validation error for a malformed URL.
    """
    response = client.post(
        "/api/v1/ai/identify-from-image",
        json={"image_url": "not-a-valid-url"},
    )
    
    assert response.status_code == 422  # Unprocessable Entity for Pydantic validation errors
