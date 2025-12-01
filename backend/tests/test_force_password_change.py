"""
Tests for force password change functionality.

This module tests the force password change feature which requires users
(typically those created by admins) to change their password on first login.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src import models
from src.crud import user as user_crud


@pytest.mark.db
def test_admin_creates_user_with_force_password_change(
    client: TestClient, db: Session, test_admin_user: models.User
) -> None:
    """
    Test that when an admin creates a user without explicitly setting
    force_password_change, it defaults to True.
    """
    # Login as admin
    login_data = {
        "username": test_admin_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    admin_token = login_response.json()["access_token"]
    
    # Create a new user (without explicitly setting force_password_change)
    new_user_data = {
        "email": "newuser@test.com",
        "password": "NewUserPass123!",
        "first_name": "New",
        "last_name": "User",
        "user_type": "employee"
    }
    
    response = client.post(
        "/api/v1/users/",
        json=new_user_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    created_user = response.json()
    
    # Verify force_password_change is True (default for admin-created users)
    assert created_user["force_password_change"] is True


@pytest.mark.db
def test_admin_creates_user_explicit_force_password_false(
    client: TestClient, db: Session, test_admin_user: models.User
) -> None:
    """
    Test that admin can explicitly set force_password_change to False
    when creating a user.
    """
    # Login as admin
    login_data = {
        "username": test_admin_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    admin_token = login_response.json()["access_token"]
    
    # Create a new user with force_password_change explicitly set to False
    new_user_data = {
        "email": "noforce@test.com",
        "password": "NoForcePass123!",
        "first_name": "No",
        "last_name": "Force",
        "user_type": "employee",
        "force_password_change": False
    }
    
    response = client.post(
        "/api/v1/users/",
        json=new_user_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    created_user = response.json()
    
    # Verify force_password_change is False as explicitly set
    assert created_user["force_password_change"] is False


@pytest.mark.db
def test_user_self_registration_no_force_password_change(
    client: TestClient, db: Session
) -> None:
    """
    Test that users who self-register (no auth) don't get force_password_change.
    """
    # Create user without authentication (self-registration)
    new_user_data = {
        "email": "selfreg@test.com",
        "password": "SelfRegPass123!",
        "first_name": "Self",
        "last_name": "Registered",
        "user_type": "customer"
    }
    
    response = client.post("/api/v1/users/", json=new_user_data)
    
    assert response.status_code == 200
    created_user = response.json()
    
    # Self-registered users should not have force_password_change
    assert created_user["force_password_change"] is False


@pytest.mark.db
def test_force_password_change_cleared_after_password_update(
    client: TestClient, db: Session, test_admin_user: models.User
) -> None:
    """
    Test that force_password_change is cleared to False after user
    updates their password via the change password endpoint.
    """
    # Admin creates a user (will have force_password_change=True)
    login_data = {
        "username": test_admin_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    admin_token = login_response.json()["access_token"]
    
    new_user_data = {
        "email": "forcechange@test.com",
        "password": "InitialPass123!",
        "first_name": "Force",
        "last_name": "Change",
        "user_type": "employee"
    }
    
    create_response = client.post(
        "/api/v1/users/",
        json=new_user_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert create_response.status_code == 200
    created_user = create_response.json()
    assert created_user["force_password_change"] is True
    
    # Login as the new user
    user_login = {
        "username": "forcechange@test.com",
        "password": "InitialPass123!"
    }
    user_login_response = client.post("/api/v1/users/login/access-token", data=user_login)
    assert user_login_response.status_code == 200
    user_token = user_login_response.json()["access_token"]
    
    # Change password
    password_change_data = {
        "current_password": "InitialPass123!",
        "new_password": "NewSecurePass123!"
    }
    
    password_response = client.post(  # Changed from PUT to POST
        "/api/v1/users/change-password",
        json=password_change_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    assert password_response.status_code == 200
    
    # Get user details to verify force_password_change is now False
    user_response = client.get(
        f"/api/v1/users/{created_user['id']}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert user_response.status_code == 200
    updated_user = user_response.json()
    
    # Verify force_password_change is now False
    assert updated_user["force_password_change"] is False


@pytest.mark.db
def test_force_password_change_persists_in_database(
    client: TestClient, db: Session, test_admin_user: models.User
) -> None:
    """
    Test that force_password_change value is properly persisted
    to the database and can be retrieved.
    """
    # Admin creates a user
    login_data = {
        "username": test_admin_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    admin_token = login_response.json()["access_token"]
    
    new_user_data = {
        "email": "persistent@test.com",
        "password": "PersistPass123!",
        "first_name": "Persist",
        "last_name": "Test",
        "user_type": "employee"
    }
    
    create_response = client.post(
        "/api/v1/users/",
        json=new_user_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    created_user = create_response.json()
    
    # Query the database directly to verify persistence
    db_user = user_crud.get_by_email(db, email="persistent@test.com")
    assert db_user is not None
    assert db_user.force_password_change is True
    
    # Also verify via API
    user_response = client.get(
        f"/api/v1/users/{created_user['id']}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert user_response.status_code == 200
    assert user_response.json()["force_password_change"] is True


@pytest.mark.db
def test_non_admin_creates_user_without_force_password_change(
    client: TestClient, db: Session, test_employee_user: models.User
) -> None:
    """
    Test that when a non-admin user creates another user,
    force_password_change is NOT automatically set to True
    (only admins get this default behavior).
    """
    # Login as employee (non-admin)
    login_data = {
        "username": test_employee_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    employee_token = login_response.json()["access_token"]
    
    # Create a user as non-admin (if allowed by system)
    new_user_data = {
        "email": "nonforce@test.com",
        "password": "NonForcePass123!",
        "first_name": "Non",
        "last_name": "Force",
        "user_type": "customer"
    }
    
    response = client.post(
        "/api/v1/users/",
        json=new_user_data,
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    
    # If the system allows employee user creation, verify force_password_change is False
    if response.status_code == 200:
        created_user = response.json()
        # Non-admin created users should not have force_password_change default to True
        assert created_user["force_password_change"] is False
    else:
        # If the system doesn't allow it, that's also valid
        assert response.status_code in [401, 403]


@pytest.mark.db
def test_admin_updates_user_force_password_change(
    client: TestClient, db: Session, test_admin_user: models.User, test_employee_user: models.User
) -> None:
    """
    Test that an admin can update a user's force_password_change flag
    via the user update endpoint.
    """
    # Login as admin
    login_data = {
        "username": test_admin_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    admin_token = login_response.json()["access_token"]
    
    # Update employee user to force password change
    update_data = {
        "force_password_change": True
    }
    
    response = client.put(
        f"/api/v1/users/{test_employee_user.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    updated_user = response.json()
    assert updated_user["force_password_change"] is True
    
    # Verify in database
    db.refresh(test_employee_user)
    assert test_employee_user.force_password_change is True


@pytest.mark.db
def test_user_cannot_change_own_force_password_change_flag(
    client: TestClient, db: Session, test_employee_user: models.User
) -> None:
    """
    Test that a regular user cannot change their own force_password_change flag
    via profile update (only admins can do this).
    """
    # First, set force_password_change to True on the employee
    test_employee_user.force_password_change = True
    db.add(test_employee_user)
    db.commit()
    
    # Login as employee
    login_data = {
        "username": test_employee_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    employee_token = login_response.json()["access_token"]
    
    # Try to update own profile to set force_password_change to False
    update_data = {
        "force_password_change": False
    }
    
    response = client.put(
        "/api/v1/users/profile",
        json=update_data,
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    
    # Should succeed but force_password_change shouldn't change
    # (profile endpoint doesn't allow changing this field)
    assert response.status_code == 200
    
    # Verify force_password_change is still True
    db.refresh(test_employee_user)
    assert test_employee_user.force_password_change is True
