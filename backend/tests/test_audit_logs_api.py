import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta


from src.models.user import User
from src.models.user_audit_log import UserAuditLog
from src.config import settings

pytestmark = pytest.mark.db

@pytest.fixture
def audit_log_data(db: Session, test_admin_user: User, test_customer_user: User):
    # Create some audit logs
    log1 = UserAuditLog(
        user_id=test_customer_user.id,
        action_performed_by=test_admin_user.id,
        action="update",
        details="Updated user profile",
        created_at=datetime.utcnow() - timedelta(days=1)
    )
    log2 = UserAuditLog(
        user_id=test_customer_user.id,
        action_performed_by=test_admin_user.id,
        action="delete",
        details="Deleted user",
        created_at=datetime.utcnow()
    )
    db.add(log1)
    db.add(log2)
    db.commit()
    return [log1, log2]

@pytest.fixture
def normal_user_headers(client: TestClient, test_customer_user: User) -> dict:
    login_data = {
        "username": test_customer_user.email,
        "password": "TestPassword123!"
    }
    r = client.post(f"{settings.API_V1_STR}/users/login/access-token", data=login_data)
    tokens = r.json()
    a_token = tokens["access_token"]
    return {"Authorization": f"Bearer {a_token}"}

def test_read_audit_logs_superuser(
    client: TestClient, 
    admin_headers: dict, 
    audit_log_data
):
    response = client.get(f"{settings.API_V1_STR}/audit-logs", headers=admin_headers)
    assert response.status_code == 200
    content = response.json()
    assert len(content) >= 2
    assert any(log["action"] == "update" for log in content)
    assert any(log["action"] == "delete" for log in content)

def test_read_audit_logs_normal_user(
    client: TestClient, 
    normal_user_headers: dict
):
    response = client.get(f"{settings.API_V1_STR}/audit-logs", headers=normal_user_headers)
    assert response.status_code == 403

def test_read_audit_logs_filter_action(
    client: TestClient, 
    admin_headers: dict, 
    audit_log_data
):
    response = client.get(
        f"{settings.API_V1_STR}/audit-logs?action=update", 
        headers=admin_headers
    )
    assert response.status_code == 200
    content = response.json()
    assert len(content) >= 1
    for log in content:
        assert log["action"] == "update"

def test_read_audit_logs_filter_date(
    client: TestClient, 
    admin_headers: dict, 
    audit_log_data
):
    # Filter for logs created in the last hour
    start_date = (datetime.utcnow() - timedelta(minutes=30)).isoformat()
    response = client.get(
        f"{settings.API_V1_STR}/audit-logs?start_date={start_date}", 
        headers=admin_headers
    )
    assert response.status_code == 200
    content = response.json()
    # Should only get the "delete" log created recently
    assert len(content) >= 1
    for log in content:
        assert log["action"] == "delete"
