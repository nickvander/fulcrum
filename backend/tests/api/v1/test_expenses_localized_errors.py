"""Localized error wire-shape tests for expenses.py.

Covers the most distinct codes (notFound, receiptNotFound,
invalidReceiptFileType) rather than 1:1 by raise site.
"""
import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.mark.db
def test_get_missing_expense_returns_localized_notFound(
    client: TestClient, admin_headers: dict
):
    response = client.get("/api/v1/expenses/999999", headers=admin_headers)

    assert response.status_code == 404
    body = response.json()
    assert body == {
        "detail": "Expense not found",
        "code": "apiErrors.expense.notFound",
        "params": {"id": 999999},
    }


@pytest.mark.db
def test_delete_missing_receipt_returns_localized_receiptNotFound(
    client: TestClient, admin_headers: dict
):
    response = client.delete(
        "/api/v1/expenses/receipts/999999", headers=admin_headers
    )

    assert response.status_code == 404
    body = response.json()
    assert body == {
        "detail": "Receipt not found",
        "code": "apiErrors.expense.receiptNotFound",
        "params": {"id": 999999},
    }


@pytest.mark.db
def test_upload_receipt_with_invalid_file_type_returns_localized_payload(
    client: TestClient, admin_headers: dict, db: Session
):
    """The upload endpoint rejects unsupported extensions before touching disk."""
    from datetime import date

    from src.crud import crud_expense
    from src.schemas import expense as expense_schema

    expense = crud_expense.expense.create(
        db,
        obj_in=expense_schema.ExpenseCreate(
            description="Test expense for receipt upload",
            amount=10.0,
            category="Other",
            date=date.today(),
        ),
    )
    db.commit()

    response = client.post(
        f"/api/v1/expenses/{expense.id}/receipts",
        headers=admin_headers,
        files={"file": ("evil.exe", io.BytesIO(b"not a real receipt"), "application/octet-stream")},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "apiErrors.expense.invalidReceiptFileType"
    assert body["params"] == {"extension": ".exe"}
    assert "Invalid file type" in body["detail"]
