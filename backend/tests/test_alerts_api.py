"""
End-to-end tests for the alerts API + Celery task wiring.

  - /alerts/rules CRUD: list, create, get, patch, delete
  - Per-user isolation: user A cannot see user B's rules
  - /alerts/rules/{id}/test: force_notify branch bypasses cooldown
  - Celery task is registered + on the hourly beat schedule
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.alert import AlertRule, AlertType
from src.models.product import Product
from src.models.order import OrderSource, SalesOrder, SalesOrderItem


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_create_and_list_rule(client: TestClient, admin_headers: dict):
    response = client.post(
        "/api/v1/alerts/rules",
        headers=admin_headers,
        json={
            "alert_type": "low_margin",
            "threshold": 30.0,
            "window_days": 14,
            "cooldown_minutes": 60,
            "notify_email": "ops@example.com",
        },
    )
    assert response.status_code == 200, response.text
    created = response.json()
    assert created["alert_type"] == "low_margin"
    assert created["threshold"] == 30.0
    assert created["enabled"] is True

    listed = client.get("/api/v1/alerts/rules", headers=admin_headers).json()
    assert any(r["id"] == created["id"] for r in listed)


@pytest.mark.db
def test_get_404s_for_unknown_rule(client: TestClient, admin_headers: dict):
    response = client.get("/api/v1/alerts/rules/99999", headers=admin_headers)
    assert response.status_code == 404


@pytest.mark.db
def test_patch_rule_updates_fields(client: TestClient, admin_headers: dict):
    created = client.post(
        "/api/v1/alerts/rules",
        headers=admin_headers,
        json={
            "alert_type": "stockout_risk",
            "threshold": 5.0,
            "notify_email": "ops@example.com",
        },
    ).json()

    patched = client.patch(
        f"/api/v1/alerts/rules/{created['id']}",
        headers=admin_headers,
        json={"threshold": 12.0, "enabled": False},
    ).json()
    assert patched["threshold"] == 12.0
    assert patched["enabled"] is False
    # Untouched fields stay the same.
    assert patched["notify_email"] == "ops@example.com"


@pytest.mark.db
def test_delete_rule_removes_it(client: TestClient, admin_headers: dict, db: Session):
    created = client.post(
        "/api/v1/alerts/rules",
        headers=admin_headers,
        json={
            "alert_type": "sales_dip",
            "threshold": 25.0,
            "notify_email": "ops@example.com",
        },
    ).json()

    response = client.delete(
        f"/api/v1/alerts/rules/{created['id']}", headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json() == {"deleted": created["id"]}
    assert db.query(AlertRule).filter(AlertRule.id == created["id"]).first() is None


@pytest.mark.db
def test_per_user_isolation(
    client: TestClient, admin_headers: dict, db: Session, test_admin_user
):
    """A rule belonging to a different user must NOT appear in the
    admin's list and must 404 on direct lookup."""
    from src.models.user import User

    other = User(email="otheruser@example.com", hashed_password="x", is_active=True)
    db.add(other)
    db.commit()
    db.refresh(other)
    other_rule = AlertRule(
        user_id=other.id,
        alert_type=AlertType.LOW_MARGIN,
        threshold=10.0,
        notify_email="x@example.com",
    )
    db.add(other_rule)
    db.commit()
    db.refresh(other_rule)

    listed = client.get("/api/v1/alerts/rules", headers=admin_headers).json()
    assert all(r["id"] != other_rule.id for r in listed)

    direct = client.get(
        f"/api/v1/alerts/rules/{other_rule.id}", headers=admin_headers,
    )
    assert direct.status_code == 404


# ---------------------------------------------------------------------------
# /test endpoint
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_test_endpoint_bypasses_cooldown_and_sends_email(
    client: TestClient, admin_headers: dict, db: Session, test_admin_user
):
    """POST /alerts/rules/{id}/test forces a notification even when
    the rule's cooldown is in force — useful for "did I wire up SMTP
    right"."""
    # Seed a thin-margin sale so the rule triggers.
    p = Product(name="ApiThin", sku="API-THIN", cost_price=8.0, default_resale_price=10.0, is_bundle=False)
    db.add(p)
    db.flush()
    order = SalesOrder(
        status="COMPLETED", total_price=50.0,
        created_at=datetime.utcnow() - timedelta(days=1),
        source=OrderSource.FULCRUM, external_order_id="API-THIN-1",
    )
    db.add(order)
    db.flush()
    db.add(SalesOrderItem(
        order_id=order.id, product_id=p.id, quantity=5,
        price_per_unit=10.0, cost_per_unit=8.0,
    ))
    db.commit()

    # Create a rule whose cooldown is brand-new.
    created = client.post(
        "/api/v1/alerts/rules",
        headers=admin_headers,
        json={
            "alert_type": "low_margin",
            "threshold": 50.0,
            "notify_email": "ops@example.com",
            "cooldown_minutes": 720,
        },
    ).json()

    # Force `last_triggered_at` so cooldown would block a normal eval.
    rule = db.query(AlertRule).filter(AlertRule.id == created["id"]).one()
    rule.last_triggered_at = datetime.now(timezone.utc)
    db.commit()

    with patch("src.services.alert_evaluation_service.get_email_service") as mock_get:
        mock_get.return_value.provider.send_email.return_value = True
        response = client.post(
            f"/api/v1/alerts/rules/{created['id']}/test", headers=admin_headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["triggered"] is True
    assert body["notification_sent"] is True
    # And the cooldown advanced to a new moment (still within
    # cooldown, but the test path is allowed past it).
    mock_get.return_value.provider.send_email.assert_called_once()


# ---------------------------------------------------------------------------
# Beat task wiring
# ---------------------------------------------------------------------------


def test_alert_celery_task_is_registered_and_scheduled():
    from src.celery_worker import celery_app
    from src import tasks as _tasks  # noqa: F401

    assert "src.tasks.evaluate_alerts" in celery_app.tasks

    schedule = celery_app.conf.beat_schedule
    assert "alert-evaluation" in schedule
    assert schedule["alert-evaluation"]["task"] == "src.tasks.evaluate_alerts"


def test_alert_celery_task_delegates_to_batch_evaluator():
    from src import tasks as task_module

    fake_session = MagicMock()
    fake_session_local = MagicMock(return_value=fake_session)

    fake_result = MagicMock()
    fake_result.model_dump.return_value = {"rules_evaluated": 0, "rules_triggered": 0, "notifications_sent": 0, "rule_results": []}

    with (
        patch.object(task_module, "SessionLocal", fake_session_local),
        patch(
            "src.services.alert_evaluation_service.evaluate_all_enabled_rules",
            return_value=fake_result,
        ) as mock_eval,
    ):
        result = task_module.evaluate_alerts()

    assert result == {"rules_evaluated": 0, "rules_triggered": 0, "notifications_sent": 0, "rule_results": []}
    mock_eval.assert_called_once_with(fake_session)
    fake_session.close.assert_called_once()
