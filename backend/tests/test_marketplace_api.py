import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

@pytest.mark.db
def test_create_marketplace(client: TestClient):
    """
    Test creating a marketplace successfully.
    """
    response = client.post(
        "/api/v1/marketplace/",
        json={"name": "Test Marketplace", "api_base_url": "https://api.test.com"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Marketplace"
    assert "id" in data

@pytest.mark.db
def test_read_marketplaces(client: TestClient):
    """
    Test reading a list of marketplaces.
    """
    # Create a marketplace first
    client.post(
        "/api/v1/marketplace/",
        json={"name": "Another Marketplace"},
    )

    response = client.get("/api/v1/marketplace/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "Another Marketplace" in [m["name"] for m in data]


@pytest.mark.db
def test_read_marketplace_listings_includes_product_names(
    client: TestClient, db: Session
):
    """
    Listing route should resolve before marketplace id and include product names.
    """
    from src.models.marketplace import Marketplace, MarketplaceListing
    from src.models.product import Product

    marketplace = Marketplace(name="Listing Test", api_base_url="https://api.test.com")
    db.add(marketplace)
    product = Product(
        name="Listing Product",
        sku="LISTING-PRODUCT-001",
        default_resale_price=20.0,
        cost_price=10.0,
    )
    db.add(product)
    db.flush()
    db.add(
        MarketplaceListing(
            product_id=product.id,
            marketplace_id=marketplace.id,
            external_listing_id="EXT-001",
            listing_url="https://example.test/listing/EXT-001",
            status="active",
            sync_status="SYNCED",
            marketplace_price=19.0,
        )
    )
    db.commit()

    response = client.get("/api/v1/marketplace/listings/")

    assert response.status_code == 200
    data = response.json()
    listing = next(item for item in data if item["external_listing_id"] == "EXT-001")
    assert listing["product_name"] == "Listing Product"


@pytest.mark.db
def test_marketplace_listings_query_count_stays_bounded(
    client: TestClient, db: Session
):
    """
    Marketplace listing reads should eager-load products instead of querying per row.
    """
    from src.models.marketplace import Marketplace, MarketplaceListing
    from src.models.product import Product

    marketplace = Marketplace(name="Query Count Marketplace", api_base_url="https://api.test.com")
    db.add(marketplace)
    db.flush()

    for index in range(8):
        product = Product(
            name=f"Marketplace Product {index}",
            sku=f"MARKETPLACE-PRODUCT-{index}",
            default_resale_price=20.0,
            cost_price=10.0,
        )
        db.add(product)
        db.flush()
        db.add(
            MarketplaceListing(
                product_id=product.id,
                marketplace_id=marketplace.id,
                external_listing_id=f"EXT-{index}",
                status="active",
                sync_status="SYNCED",
            )
        )
    db.commit()

    statements = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(db.bind, "before_cursor_execute", before_cursor_execute)
    try:
        response = client.get("/api/v1/marketplace/listings/?limit=100")
    finally:
        event.remove(db.bind, "before_cursor_execute", before_cursor_execute)

    assert response.status_code == 200
    assert len(response.json()) >= 8
    assert len(statements) <= 3
