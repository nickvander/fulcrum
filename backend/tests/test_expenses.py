import pytest
from fastapi.testclient import TestClient
from src.crud.crud_expense import expense as crud_expense
from src.schemas.expense import ExpenseCreate
from datetime import date

@pytest.mark.db
def test_create_expense(db, client: TestClient, admin_headers):
    data = {
        "description": "Office Rent",
        "amount": 1200.0,
        "category": "Rent",
        "date": str(date.today())
    }
    response = client.post("/api/v1/expenses/", json=data, headers=admin_headers)
    assert response.status_code == 200
    content = response.json()
    assert content["description"] == data["description"]
    assert content["amount"] == 1200.0
    assert "id" in content

@pytest.mark.db
def test_read_expenses(db, client: TestClient, admin_headers):
    crud_expense.create(db, obj_in=ExpenseCreate(
        description="Software Subscription",
        amount=50.0,
        category="Software",
        date=date.today()
    ))
    response = client.get("/api/v1/expenses/", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1
