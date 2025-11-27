"""
Tests for audit logging functionality
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src import crud, models
from src.models.user_audit_log import UserAuditLog

# Mark all tests in this module as database-dependent
pytestmark = pytest.mark.db


def test_audit_log_creation_on_deactivation(client: TestClient, db: Session, test_admin_user: models.User) -> None:
    """Test that deactivating a user creates an audit log entry"""
    # Create a user to deactivate
    user_data = {
        "email": "audit_deactivate@test.com",
        "password": "TestPass123!",
        "first_name": "Audit",
        "last_name": "Deactivate",
        "user_type": "employee"
    }
    create_response = client.post("/api/v1/users/", json=user_data)
    assert create_response.status_code == 200
    user = create_response.json()
    
    # Login as admin
    login_data = {
        "username": test_admin_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    
    # Deactivate the user
    response = client.delete(f"/api/v1/users/{user['id']}", 
                           headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    # Verify audit log was created
    audit_log = db.query(UserAuditLog).filter(
        UserAuditLog.user_id == user['id'],
        UserAuditLog.action == 'deactivate_user'
    ).first()
    
    assert audit_log is not None
    assert audit_log.action_performed_by == test_admin_user.id
    assert "deactivated by admin" in audit_log.details


def test_audit_log_creation_on_permanent_deletion(client: TestClient, db: Session, test_admin_user: models.User) -> None:
    """Test that permanently deleting a user creates an audit log entry"""
    # Create a user to delete
    user_data = {
        "email": "audit_delete@test.com",
        "password": "TestPass123!",
        "first_name": "Audit",
        "last_name": "Delete",
        "user_type": "employee"
    }
    create_response = client.post("/api/v1/users/", json=user_data)
    assert create_response.status_code == 200
    user = create_response.json()
    user_id = user['id']
    
    # Login as admin
    login_data = {
        "username": test_admin_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    
    # Permanently delete the user
    response = client.delete(f"/api/v1/users/{user_id}/permanent", 
                           headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    # Verify audit log was created
    # Note: For permanent deletion, the user_id in audit log might be null or preserved depending on implementation
    # Based on crud_user.py, we insert a record with action='permanent_delete'
    
    audit_log = db.query(UserAuditLog).filter(
        UserAuditLog.action == 'permanent_delete',
        UserAuditLog.action_performed_by == test_admin_user.id
    ).order_by(UserAuditLog.created_at.desc()).first()
    
    assert audit_log is not None
    assert "permanently deleted" in audit_log.details
    assert str(user['email']) in audit_log.details


def test_audit_log_creation_on_password_reset(client: TestClient, db: Session, test_employee_user: models.User) -> None:
    """Test that password reset creates an audit log entry"""
    # Create a reset token
    reset_token = crud.password_reset_token.create_reset_token(db, user_id=test_employee_user.id)
    
    # Reset password using token
    reset_data = {
        "token": reset_token.token,
        "new_password": "NewPassword123!"
    }
    
    response = client.post("/api/v1/users/password-reset", json=reset_data)
    assert response.status_code == 200
    
    # Verify audit log was created
    audit_log = db.query(UserAuditLog).filter(
        UserAuditLog.user_id == test_employee_user.id,
        UserAuditLog.action == 'password_reset'
    ).first()
    
    assert audit_log is not None
    assert audit_log.action_performed_by == test_employee_user.id
    assert audit_log.details == "Password reset using token"


def test_audit_log_creation_on_admin_password_reset(client: TestClient, db: Session, test_admin_user: models.User, test_employee_user: models.User) -> None:
    """Test that admin password reset creates an audit log entry"""
    # Login as admin
    login_data = {
        "username": test_admin_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    
    # Admin reset password
    response = client.post(f"/api/v1/users/{test_employee_user.id}/admin-reset-password",
                          headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    # Verify audit log was created
    audit_log = db.query(UserAuditLog).filter(
        UserAuditLog.user_id == test_employee_user.id,
        UserAuditLog.action == 'admin_password_reset'
    ).first()
    
    assert audit_log is not None
    assert audit_log.action_performed_by == test_admin_user.id
    assert "Password reset by admin" in audit_log.details
