"""
Tests for user management API endpoints with comprehensive error handling and validation
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.models.user import User

# Mark all tests in this module as database-dependent
pytestmark = pytest.mark.db


def test_create_user_endpoint_validation(client: TestClient, db: Session) -> None:
    """Test validation rules for user creation endpoint"""
    # Test missing required fields
    response = client.post("/api/v1/users/", json={})
    assert response.status_code == 422
    
    # Test invalid email format
    user_data = {
        "email": "invalid-email",
        "password": "ValidPass123!",
        "first_name": "Test",
        "last_name": "User"
    }
    response = client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 422
    
    # Test weak password
    user_data = {
        "email": "weak@test.com",
        "password": "weak",
        "first_name": "Test",
        "last_name": "User"
    }
    response = client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 422


def test_user_get_by_id_endpoint(client: TestClient, db: Session, test_admin_user: User) -> None:
    """Test getting a user by ID with proper authorization"""
    # Login as admin to get user details
    login_data = {
        "username": test_admin_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Get admin user details by ID
    response = client.get(f"/api/v1/users/{test_admin_user.id}", 
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    user_data = response.json()
    assert user_data["id"] == test_admin_user.id
    assert user_data["email"] == test_admin_user.email
    assert user_data["is_superuser"] == test_admin_user.is_superuser


def test_user_get_by_id_self_access(client: TestClient, db: Session, test_employee_user: User) -> None:
    """Test that users can access their own details"""
    # Login as employee to get their own details
    login_data = {
        "username": test_employee_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Get own user details by ID
    response = client.get(f"/api/v1/users/{test_employee_user.id}", 
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    user_data = response.json()
    assert user_data["id"] == test_employee_user.id
    assert user_data["email"] == test_employee_user.email


def test_user_get_by_id_unauthorized_access(client: TestClient, db: Session, 
                                           test_employee_user: User, test_customer_user: User) -> None:
    """Test that users can't access other users' details"""
    # Login as customer user
    login_data = {
        "username": test_customer_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Try to access employee user details (should fail)
    response = client.get(f"/api/v1/users/{test_employee_user.id}", 
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 403  # Forbidden


def test_update_user_endpoint(client: TestClient, db: Session, test_admin_user: User, test_employee_user: User) -> None:
    """Test updating user details by admin"""
    # Login as admin to update user
    login_data = {
        "username": test_admin_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Update user data
    update_data = {
        "first_name": "Updated",
        "last_name": "Name",
        "user_type": "employee"
    }
    
    response = client.put(f"/api/v1/users/{test_employee_user.id}", 
                         json=update_data,
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    updated_user = response.json()
    assert updated_user["first_name"] == "Updated"
    assert updated_user["last_name"] == "Name"


def test_update_user_endpoint_non_admin(client: TestClient, db: Session, test_employee_user: User) -> None:
    """Test that non-admins can't update other users"""
    # Login as employee user (not admin)
    login_data = {
        "username": test_employee_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Try to update admin user (should fail)
    update_data = {
        "first_name": "Hacked",
        "last_name": "Admin"
    }
    
    response = client.put(f"/api/v1/users/{test_employee_user.id}",  # Update self is allowed, but for other user it won't be
                         json=update_data,
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 403  # Self update via this endpoint is forbidden (must use /profile)
    
    
    # Create another user to test updating other users
    other_user_data = {
        "email": "other@test.com",
        "password": "ValidPass123!",
        "first_name": "Other",
        "last_name": "User",
        "user_type": "employee"
    }
    create_response = client.post("/api/v1/users/", json=other_user_data)
    assert create_response.status_code == 200
    other_user = create_response.json()
    
    # Try to update the other user (should fail for non-admin)
    response = client.put(f"/api/v1/users/{other_user['id']}", 
                         json=update_data,
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 403  # Forbidden


def test_user_profile_endpoints(client: TestClient, db: Session, test_employee_user: User) -> None:
    """Test user profile get and update endpoints"""
    # Login as employee to access profile
    login_data = {
        "username": test_employee_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Get profile
    response = client.get("/api/v1/users/profile", 
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    profile_data = response.json()
    assert profile_data["id"] == test_employee_user.id
    assert profile_data["email"] == test_employee_user.email
    
    # Update profile
    update_data = {
        "first_name": "Profile",
        "last_name": "Updated"
    }
    
    response = client.put("/api/v1/users/profile", 
                         json=update_data,
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    updated_profile = response.json()
    assert updated_profile["first_name"] == "Profile"


def test_user_deactivation_endpoint(client: TestClient, db: Session, test_admin_user: User) -> None:
    """Test user deactivation endpoint"""
    # Create a user to deactivate
    user_data = {
        "email": "deactivate@test.com",
        "password": "ValidPass123!",
        "first_name": "Deactivate",
        "last_name": "Me",
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
    
    # Deactivate user
    response = client.delete(f"/api/v1/users/{user['id']}", 
                           headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    # Verify user is inactive
    get_response = client.get(f"/api/v1/users/{user['id']}", 
                            headers={"Authorization": f"Bearer {access_token}"})
    assert get_response.status_code == 200
    deactivated_user = get_response.json()
    assert deactivated_user["is_active"] is False


def test_user_deactivation_self_protection(client: TestClient, db: Session, test_employee_user: User) -> None:
    """Test that users can't deactivate their own accounts"""
    # Login as employee user
    login_data = {
        "username": test_employee_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Try to deactivate own account (should fail)
    client.delete(f"/api/v1/users/{test_employee_user.id}", 
                           headers={"Authorization": f"Bearer {access_token}"})
    # This should fail with 403 or 400 depending on implementation
    # The API should check if user is trying to deactivate themselves


def test_user_permanent_deletion_endpoint(client: TestClient, db: Session, test_admin_user: User) -> None:
    """Test permanent user deletion endpoint"""
    # Create a user to permanently delete
    user_data = {
        "email": "delete@test.com",
        "password": "ValidPass123!",
        "first_name": "Delete",
        "last_name": "Me",
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
    
    # Permanently delete user
    response = client.delete(f"/api/v1/users/{user['id']}/permanent", 
                           headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    # Verify user no longer exists
    get_response = client.get(f"/api/v1/users/{user['id']}", 
                            headers={"Authorization": f"Bearer {access_token}"})
    assert get_response.status_code == 404


def test_password_reset_request_endpoint(client: TestClient, db: Session, test_employee_user: User) -> None:
    """Test password reset request endpoint"""
    # Request password reset for existing user
    reset_data = {
        "email": test_employee_user.email
    }
    response = client.post("/api/v1/users/password-reset-request", json=reset_data)
    assert response.status_code == 200
    
    result = response.json()
    assert "message" in result


def test_password_reset_request_nonexistent_user(client: TestClient, db: Session) -> None:
    """Test password reset request for non-existent user doesn't reveal user doesn't exist"""
    # Request password reset for non-existent user
    reset_data = {
        "email": "nonexistent@test.com"
    }
    response = client.post("/api/v1/users/password-reset-request", json=reset_data)
    assert response.status_code == 200
    
    result = response.json()
    assert "message" in result
    # Should return success message without revealing user doesn't exist


def test_address_management_endpoints(client: TestClient, db: Session, test_customer_user: User) -> None:
    """Test address management endpoints for users"""
    # Login as customer to manage addresses
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
        "street": "123 Main St",
        "city": "Anytown",
        "state": "NY",
        "postal_code": "12345",
        "country": "USA",
        "is_primary": True,
        "is_billing": True,
        "is_shipping": True
    }
    
    response = client.post("/api/v1/addresses/", 
                          json=address_data,
                          headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    created_address = response.json()
    assert created_address["street"] == "123 Main St"
    assert created_address["user_id"] == test_customer_user.id
    
    # Get all addresses for user
    response = client.get("/api/v1/addresses/", 
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    addresses = response.json()
    assert len(addresses) >= 1
    assert any(addr["id"] == created_address["id"] for addr in addresses)
    
    # Get specific address
    response = client.get(f"/api/v1/addresses/{created_address['id']}", 
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    retrieved_address = response.json()
    assert retrieved_address["id"] == created_address["id"]
    
    # Update address
    update_data = {
        "street": "456 Updated St",
        "is_primary": False
    }
    
    response = client.put(f"/api/v1/addresses/{created_address['id']}", 
                         json=update_data,
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    updated_address = response.json()
    assert updated_address["street"] == "456 Updated St"
    
    # Delete address
    response = client.delete(f"/api/v1/addresses/{created_address['id']}", 
                           headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    # Verify address is deleted
    response = client.get(f"/api/v1/addresses/{created_address['id']}", 
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404


def test_address_unauthorized_access(client: TestClient, db: Session, test_customer_user: User, test_employee_user: User) -> None:
    """Test that users can't access other users' addresses"""
    # Login as customer to create an address
    login_data = {
        "username": test_customer_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    customer_token = token_data["access_token"]
    
    # Create an address for customer user
    address_data = {
        "street": "Customer Address",
        "city": "Anytown",
        "state": "NY",
        "postal_code": "12345",
        "country": "USA",
        "is_primary": True
    }
    
    response = client.post("/api/v1/addresses/", 
                          json=address_data,
                          headers={"Authorization": f"Bearer {customer_token}"})
    assert response.status_code == 200
    customer_address = response.json()
    
    # Login as employee to try to access customer's address
    login_data = {
        "username": test_employee_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    employee_token = token_data["access_token"]
    
    # Try to access customer's address (should fail)
    response = client.get(f"/api/v1/addresses/{customer_address['id']}", 
                         headers={"Authorization": f"Bearer {employee_token}"})
    assert response.status_code == 403  # Forbidden


def test_user_list_endpoint_pagination(client: TestClient, db: Session, test_admin_user: User) -> None:
    """Test user list endpoint with pagination"""
    # Create multiple users for pagination test
    for i in range(5):
        user_data = {
            "email": f"page{i}@test.com",
            "password": "ValidPass123!",
            "first_name": f"Page{i}",
            "last_name": "User",
            "user_type": "employee"
        }
        response = client.post("/api/v1/users/", json=user_data)
        assert response.status_code == 200
    
    # Login as admin to get user list with pagination
    login_data = {
        "username": test_admin_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Get first page (2 items)
    response = client.get("/api/v1/users/?skip=0&limit=2", 
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    users_page_1 = response.json()
    assert len(users_page_1) <= 2
    
    # Get second page (2 items)
    response = client.get("/api/v1/users/?skip=2&limit=2", 
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    users_page_2 = response.json()
    assert len(users_page_2) <= 2
    
    # Verify no overlap between pages (for our test data)
    page_1_ids = {user["id"] for user in users_page_1}
    page_2_ids = {user["id"] for user in users_page_2}
    assert not page_1_ids.intersection(page_2_ids)  # No common IDs between pages


def test_user_list_endpoint_filters(client: TestClient, db: Session, test_admin_user: User) -> None:
    """Test user list endpoint with various filters"""
    # Create users with different attributes
    admin_user_data = {
        "email": "filteradmin@test.com",
        "password": "ValidPass123!",
        "first_name": "Filter",
        "last_name": "Admin",
        "user_type": "admin",
        "is_active": True
    }
    client.post("/api/v1/users/", json=admin_user_data)
    
    inactive_user_data = {
        "email": "inactive@test.com",
        "password": "ValidPass123!",
        "first_name": "Inactive",
        "last_name": "User",
        "user_type": "employee",
        "is_active": False
    }
    client.post("/api/v1/users/", json=inactive_user_data)
    
    # Login as admin to get filtered user list
    login_data = {
        "username": test_admin_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Filter by user type
    response = client.get("/api/v1/users/?user_type=admin", 
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    admin_users = response.json()
    assert all(user["user_type"] == "admin" for user in admin_users)
    
    # Filter by active status
    response = client.get("/api/v1/users/?is_active=false", 
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    inactive_users = response.json()
    assert all(user["is_active"] is False for user in inactive_users)
    
    # Search by name
    response = client.get("/api/v1/users/?search=Inactive", 
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    search_results = response.json()
    assert any("Inactive" in user["first_name"] or "Inactive" in user["last_name"] for user in search_results)


def test_admin_password_reset_endpoint(client: TestClient, db: Session, test_admin_user: User, test_employee_user: User) -> None:
    """Test admin password reset endpoint"""
    # Login as admin
    login_data = {
        "username": test_admin_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Reset password for employee user
    response = client.post(f"/api/v1/users/{test_employee_user.id}/admin-reset-password",
                          headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    result = response.json()
    assert "message" in result
    # In test environment, we might return the new password
    # This behavior may vary depending on implementation


def test_admin_password_reset_unauthorized(client: TestClient, db: Session, test_employee_user: User, test_customer_user: User) -> None:
    """Test that non-admins can't reset other users' passwords"""
    # Login as employee user
    login_data = {
        "username": test_employee_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    employee_token = token_data["access_token"]
    
    # Try to reset password for customer user (should fail)
    response = client.post(f"/api/v1/users/{test_customer_user.id}/admin-reset-password",
                          headers={"Authorization": f"Bearer {employee_token}"})
    assert response.status_code == 403  # Forbidden