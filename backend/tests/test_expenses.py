import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
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


@pytest.mark.db
def test_expense_summary_uses_aggregate_queries(db, client: TestClient, admin_headers):
    crud_expense.create(db, obj_in=ExpenseCreate(
        description="Software Subscription",
        amount=50.0,
        category="Software",
        date=date.today(),
        paid_by_name="Nick",
        is_reimbursed=False,
    ))
    crud_expense.create(db, obj_in=ExpenseCreate(
        description="Recurring Rent",
        amount=1200.0,
        category="Rent",
        date=date.today(),
        expense_type="recurring",
        is_reimbursed=True,
    ))

    statements = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(db.bind, "before_cursor_execute", before_cursor_execute)
    try:
        response = client.get("/api/v1/expenses/summary", headers=admin_headers)
    finally:
        event.remove(db.bind, "before_cursor_execute", before_cursor_execute)

    assert response.status_code == 200
    data = response.json()
    assert data["total_amount"] == 1250.0
    assert data["by_category"]["Software"] == 50.0
    assert data["by_category"]["Rent"] == 1200.0
    assert data["by_type"]["one_time"] == 50.0
    assert data["by_type"]["recurring"] == 1200.0
    assert data["by_user"]["Nick"] == 50.0
    assert data["unreimbursed_total"] == 50.0
    assert data["count"] >= 2
    assert len(statements) <= 4
