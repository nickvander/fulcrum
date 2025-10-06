# Task: Harden and Finalize Phase 1

## Goal

To address remaining gaps and improve the robustness of the Phase 1 backend, ensuring it is a solid foundation for future development.

## Implementation Plan

1.  **Implement Dependency Injection for Services:**
    -   Create a new `src/api/dependencies.py` file.
    -   Implement a `get_ai_service` dependency that returns the appropriate `AIService` instance.
    -   Refactor the `search_products` endpoint to use `Depends(get_ai_service)`.
    -   Update tests to override this new dependency, making them cleaner.

2.  **Add Graceful Error Handling for Unique Constraints:**
    -   In `crud_product.py`, modify the `create` method to check if a product with the given SKU already exists.
    -   If it exists, raise an `HTTPException` with a `409 Conflict` status code.
    -   Add a new test case to `test_products_api.py` to verify this behavior.

3.  **Improve Celery Testing with Mocking:**
    -   In `test_products_api.py`, use `unittest.mock.patch` to mock the `generate_product_embedding.delay` method.
    -   Uncomment the `.delay()` call in the `create_product` endpoint.
    -   In the test, assert that the mocked `.delay()` method was called with the correct product ID.

4.  **Implement Marketplace API:**
    -   Create `src/schemas/marketplace.py` with `MarketplaceCreate` and `MarketplaceUpdate` schemas.
    -   Create `src/crud/crud_marketplace.py` for database operations.
    -   Create `src/api/v1/endpoints/marketplace.py` with standard CRUD endpoints.
    -   Add the new marketplace router to the main `api_router`.
    -   Create `tests/test_marketplace_api.py` to ensure the new endpoints are working correctly.

## Validation

-   All existing and new unit tests must pass.
-   The `ruff` linter must pass with no errors.
-   The GitHub Actions CI pipeline must pass successfully.
