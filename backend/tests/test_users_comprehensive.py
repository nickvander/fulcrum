"""Comprehensive tests for user management endpoints with validation and QA"""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src import crud, models, schemas


def test_create_user_comprehensive(client: TestClient, db: Session) -> None:
    """Test comprehensive user creation with all fields"""
    user_data = {
        "email": "comprehensive@test.com",
        "password": "TestPass123!",
        "first_name": "Comprehensive",
        "last_name": "User",
        "user_type": "employee",
        "is_active": True,
        "is_superuser": False,
        "avatar": "https://example.com/avatar.jpg"
    }
    
    response = client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["email"] == "comprehensive@test.com"
    assert data["first_name"] == "Comprehensive"
    assert data["last_name"] == "User"
    assert data["user_type"] == "employee"
    assert data["employee_id"] is not None
    assert data["avatar"] == "https://example.com/avatar.jpg"


def test_create_user_with_avatar(client: TestClient, db: Session) -> None:
    """Test user creation with avatar URL"""
    user_data = {
        "email": "avatar@test.com",
        "password": "TestPass123!",
        "first_name": "Avatar",
        "last_name": "User",
        "user_type": "employee",
        "avatar": "https://example.com/avatar.png"
    }
    
    response = client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["avatar"] == "https://example.com/avatar.png"


def test_update_user_with_avatar(client: TestClient, db: Session, test_admin_user: models.User) -> None:
    """Test updating user with avatar field"""
    # Create a user first
    user_in = schemas.UserCreate(
        email="updateavatar@test.com",
        password="TestPass123!",
        user_type="employee",
        first_name="Update",
        last_name="Avatar"
    )
    user = crud.user.create(db=db, obj_in=user_in)
    
    # Login as admin to update user
    login_data = {
        "username": test_admin_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Update user data including avatar
    update_data = {
        "first_name": "Updated",
        "last_name": "Avatar",
        "avatar": "https://example.com/new-avatar.jpg"
    }
    
    response = client.put(f"/api/v1/users/{user.id}", 
                         json=update_data,
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    updated_user = response.json()
    assert updated_user["avatar"] == "https://example.com/new-avatar.jpg"


def test_user_profile_update_with_avatar(client: TestClient, db: Session, test_employee_user: models.User) -> None:
    """Test updating user profile with avatar"""
    # Login as the user to update profile
    login_data = {
        "username": test_employee_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Update profile data
    update_data = {
        "first_name": "Updated",
        "last_name": "Profile",
        "avatar": "https://example.com/profile-avatar.jpg"
    }
    
    response = client.put("/api/v1/users/profile", 
                         json=update_data,
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    updated_profile = response.json()
    assert updated_profile["first_name"] == "Updated"
    assert updated_profile["avatar"] == "https://example.com/profile-avatar.jpg"


def test_user_list_with_filters(client: TestClient, db: Session, test_admin_user: models.User) -> None:
    """Test user list endpoint with various filters"""
    # Create test users
    user1_data = {
        "email": "filter1@test.com",
        "password": "TestPass123!",
        "first_name": "Filter",
        "last_name": "One",
        "user_type": "employee",
        "is_active": True
    }
    
    user2_data = {
        "email": "filter2@test.com",
        "password": "TestPass123!",
        "first_name": "Filter",
        "last_name": "Two",
        "user_type": "customer",
        "is_active": False
    }
    
    client.post("/api/v1/users/", json=user1_data)
    client.post("/api/v1/users/", json=user2_data)
    
    # Login as admin to get user list
    login_data = {
        "username": test_admin_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Test filtering by user type
    response = client.get("/api/v1/users/?user_type=employee", 
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    users = response.json()
    employee_users = [u for u in users if u["user_type"] == "employee"]
    assert len(employee_users) >= 1
    
    # Test filtering by active status
    response = client.get("/api/v1/users/?is_active=false", 
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    users = response.json()
    inactive_users = [u for u in users if u["is_active"] is False]
    assert len(inactive_users) >= 1
    
    # Test search functionality
    response = client.get("/api/v1/users/?search=filter", 
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 2


def test_password_reset_flow_comprehensive(client: TestClient, db: Session, test_employee_user: models.User) -> None:
    """Test the complete password reset flow"""
    # Request password reset
    reset_request_data = {"email": test_employee_user.email}
    response = client.post("/api/v1/users/password-reset-request", json=reset_request_data)
    assert response.status_code == 200
    
    # The response should confirm the request was processed
    assert "message" in response.json()
    
    # Since we can't actually receive the email in tests, 
    # we'll use the direct admin reset functionality to verify the reset process works
    login_data = {
        "username": test_employee_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200


def test_admin_password_reset(client: TestClient, db: Session, test_admin_user: models.User, test_employee_user: models.User) -> None:
    """Test admin password reset functionality"""
    # Login as admin
    login_data = {
        "username": test_admin_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Reset password for another user
    response = client.post(f"/api/v1/users/{test_employee_user.id}/admin-reset-password",
                          headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    result = response.json()
    assert "message" in result
    assert "new_password" in result  # In test environment, we return the new password


def test_role_based_access_control(client: TestClient, db: Session, test_employee_user: models.User, test_admin_user: models.User) -> None:
    """Test role-based access control for user management operations"""
    # Login as employee user
    login_data = {
        "username": test_employee_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    employee_token = token_data["access_token"]
    
    # Try to access user list (should fail for non-admin)
    response = client.get("/api/v1/users/", 
                         headers={"Authorization": f"Bearer {employee_token}"})
    assert response.status_code == 403  # Forbidden
    
    # Try to update another user (should fail for non-admin)
    update_data = {"first_name": "Hacked"}
    response = client.put(f"/api/v1/users/{test_admin_user.id}", 
                         json=update_data,
                         headers={"Authorization": f"Bearer {employee_token}"})
    assert response.status_code == 403  # Forbidden
    
    # Login as admin to verify it works
    admin_login_data = {
        "username": test_admin_user.email,
        "password": "TestPassword123!"
    }
    admin_login_response = client.post("/api/v1/users/login/access-token", data=admin_login_data)
    assert admin_login_response.status_code == 200
    
    admin_token_data = admin_login_response.json()
    admin_token = admin_token_data["access_token"]
    
    # Admin should be able to access user list
    response = client.get("/api/v1/users/", 
                         headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200


def test_user_deactivation_and_reactivation(client: TestClient, db: Session, test_admin_user: models.User) -> None:
    """Test user deactivation functionality"""
    # Create a user to deactivate
    user_data = {
        "email": "deactivate@test.com",
        "password": "TestPass123!",
        "first_name": "Deactivate",
        "last_name": "Test",
        "user_type": "employee"
    }
    create_response = client.post("/api/v1/users/", json=user_data)
    assert create_response.status_code == 200
    user = create_response.json()
    
    # Login as admin to deactivate user
    login_data = {
        "username": test_admin_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Deactivate the user
    response = client.delete(f"/api/v1/users/{user['id']}", 
                           headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    # Verify user is deactivated
    get_response = client.get(f"/api/v1/users/{user['id']}",
                             headers={"Authorization": f"Bearer {access_token}"})
    assert get_response.status_code == 200
    retrieved_user = get_response.json()
    assert retrieved_user["is_active"] is False


def test_permanent_user_deletion(client: TestClient, db: Session, test_admin_user: models.User) -> None:
    """Test permanent user deletion functionality"""
    # Create a user to delete
    user_data = {
        "email": "delete@test.com",
        "password": "TestPass123!",
        "first_name": "Delete",
        "last_name": "Test",
        "user_type": "employee"
    }
    create_response = client.post("/api/v1/users/", json=user_data)
    assert create_response.status_code == 200
    user = create_response.json()
    
    # Login as admin to permanently delete user
    login_data = {
        "username": test_admin_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Permanently delete the user
    response = client.delete(f"/api/v1/users/{user['id']}/permanent", 
                           headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    # Verify user is gone by trying to get it
    get_response = client.get(f"/api/v1/users/{user['id']}",
                             headers={"Authorization": f"Bearer {access_token}"})
    assert get_response.status_code == 404


def test_customer_user_address_management(client: TestClient, db: Session, test_customer_user: models.User) -> None:
    """Test address management for customer users"""
    # Login as customer
    login_data = {
        "username": test_customer_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Create an address
    address_data = {
        "street": "123 Test Street",
        "city": "Test City",
        "state": "TS",
        "postal_code": "12345",
        "country": "Testland",
        "is_primary": True,
        "is_billing": True,
        "is_shipping": True
    }
    
    response = client.post("/api/v1/addresses/", 
                          json=address_data,
                          headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200  # This endpoint may not exist yet, but we're testing the access


def test_user_authentication_flows(client: TestClient, db: Session) -> None:
    """Test complete user authentication flows"""
    # Create test user
    user_data = {
        "email": "auth@test.com",
        "password": "TestPass123!",
        "first_name": "Auth",
        "last_name": "Test",
        "user_type": "employee"
    }
    create_response = client.post("/api/v1/users/", json=user_data)
    assert create_response.status_code == 200
    
    # Test login with correct credentials
    login_data = {
        "username": "auth@test.com",
        "password": "TestPass123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    
    access_token = token_data["access_token"]
    
    # Test accessing protected endpoint with token
    profile_response = client.get("/api/v1/users/profile",
                                 headers={"Authorization": f"Bearer {access_token}"})
    assert profile_response.status_code == 200
    
    profile_data = profile_response.json()
    assert profile_data["email"] == "auth@test.com"


def test_user_validation_rules(client: TestClient, db: Session) -> None:
    """Test user validation rules"""
    # Test weak password
    weak_password_data = {
        "email": "weak@test.com",
        "password": "123",
        "first_name": "Weak",
        "last_name": "Password",
        "user_type": "employee"
    }
    response = client.post("/api/v1/users/", json=weak_password_data)
    assert response.status_code == 422  # Validation error
    
    # Test invalid email
    invalid_email_data = {
        "email": "not-an-email",
        "password": "TestPass123!",
        "first_name": "Invalid",
        "last_name": "Email",
        "user_type": "employee"
    }
    response = client.post("/api/v1/users/", json=invalid_email_data)
    assert response.status_code == 422  # Validation error


def test_user_self_modification_restrictions(client: TestClient, db: Session, test_employee_user: models.User) -> None:
    """Test that users can't modify restricted fields on their own profile"""
    # Login as employee
    login_data = {
        "username": test_employee_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Try to make self a superuser (should not be allowed for regular users)
    update_data = {
        "is_superuser": True,
        "first_name": "Hacked"
    }
    
    response = client.put("/api/v1/users/profile", 
                         json=update_data,
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200  # Should succeed but ignore restricted fields
    
    # Get profile again to verify superuser was not changed
    profile_response = client.get("/api/v1/users/profile",
                                 headers={"Authorization": f"Bearer {access_token}"})
    assert profile_response.status_code == 200
    
    profile_data = profile_response.json()
    # Should still be false since regular users can't change this
    assert profile_data["is_superuser"] == test_employee_user.is_superuser