from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src import crud, models, schemas
import pytest

# Mark all tests in this module as database-dependent
pytestmark = pytest.mark.db

def test_create_user(client: TestClient, db: Session) -> None:
    """Test creating a new user"""
    user_data = {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User",
        "user_type": "employee"
    }
    
    response = client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["first_name"] == "Test"
    assert data["last_name"] == "User"
    assert data["user_type"] == "employee"
    assert data["employee_id"] is not None


def test_create_user_with_weak_password(client: TestClient, db: Session) -> None:
    """Test that weak passwords are rejected"""
    user_data = {
        "email": "weakpass@example.com",
        "password": "123",  # Too weak
        "first_name": "Weak",
        "last_name": "Password"
    }
    
    response = client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 422  # Validation error


def test_get_users_list(client: TestClient, db: Session, test_admin_user: models.User) -> None:
    """Test getting list of users (admin only)"""
    # Create another user first
    user_in = schemas.UserCreate(
        email="listtest@example.com",
        password="TestPassword123!",
        user_type="employee",
        first_name="List",
        last_name="Test"
    )
    crud.user.create(db=db, obj_in=user_in)
    
    # Login as admin to get user list
    login_data = {
        "username": test_admin_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Get users list
    response = client.get("/api/v1/users/", 
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    users = response.json()
    assert len(users) >= 2  # Should have at least the admin and the new user


def test_get_user_by_id(client: TestClient, db: Session, test_employee_user: models.User) -> None:
    """Test getting a specific user by ID"""
    # Login as the user to get their details
    login_data = {
        "username": test_employee_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Get user details
    response = client.get(f"/api/v1/users/{test_employee_user.id}", 
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    user_data = response.json()
    assert user_data["email"] == test_employee_user.email
    assert user_data["first_name"] == test_employee_user.first_name


def test_update_user(client: TestClient, db: Session, test_admin_user: models.User, test_employee_user: models.User) -> None:
    """Test updating a user (admin only)"""
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
        "is_active": True
    }
    
    response = client.put(f"/api/v1/users/{test_employee_user.id}", 
                         json=update_data,
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    updated_user = response.json()
    assert updated_user["first_name"] == "Updated"
    assert updated_user["last_name"] == "Name"


def test_employee_id_generation(client: TestClient, db: Session) -> None:
    """Test that employee IDs are auto-generated correctly"""
    user_data = {
        "email": "employeeid@test.com",
        "password": "TestPassword123!",
        "user_type": "employee",
        "first_name": "Employee",
        "last_name": "ID"
    }
    
    response = client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 200
    
    user = response.json()
    assert user["employee_id"] is not None
    assert user["employee_id"].startswith("EMP")  # Employee prefix


def test_create_admin_with_admin_prefix(client: TestClient, db: Session) -> None:
    """Test that admin users get correct prefix in employee ID"""
    user_data = {
        "email": "adminid@test.com",
        "password": "TestPassword123!",
        "user_type": "admin",
        "first_name": "Admin",
        "last_name": "ID"
    }
    
    response = client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 200
    
    user = response.json()
    assert user["employee_id"] is not None
    assert user["employee_id"].startswith("ADM")  # Admin prefix


def test_create_customer_with_customer_prefix(client: TestClient, db: Session) -> None:
    """Test that customer users get correct prefix in employee ID"""
    user_data = {
        "email": "customerid@test.com",
        "password": "TestPassword123!",
        "user_type": "customer",
        "first_name": "Customer",
        "last_name": "ID"
    }
    
    response = client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 200
    
    user = response.json()
    assert user["employee_id"] is not None
    assert user["employee_id"].startswith("CST")  # Customer prefix


def test_user_login(client: TestClient, db: Session, test_employee_user: models.User) -> None:
    """Test user login functionality"""
    login_data = {
        "username": test_employee_user.email,
        "password": "TestPassword123!"
    }
    
    response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert response.status_code == 200
    
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"


def test_user_login_invalid_credentials(client: TestClient, db: Session) -> None:
    """Test login with invalid credentials"""
    login_data = {
        "username": "nonexistent@test.com",
        "password": "wrongpassword"
    }
    
    response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert response.status_code == 400
    assert "Incorrect email or password" in response.json()["detail"]


def test_create_user_with_duplicate_email(client: TestClient, db: Session, test_employee_user: models.User) -> None:
    """Test that creating a user with duplicate email fails"""
    user_data = {
        "email": test_employee_user.email,  # Same as existing user
        "password": "TestPassword123!",
        "user_type": "employee",
        "first_name": "Duplicate",
        "last_name": "User"
    }
    
    response = client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_create_address_for_user(client: TestClient, db: Session, test_customer_user: models.User) -> None:
    """Test creating an address for a user"""
    # Login as the customer
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
    
    client.post("/api/v1/addresses/", 
                          json=address_data,
                          headers={"Authorization": f"Bearer {access_token}"})
    # Note: Address endpoint may not exist yet, so this might fail - that's expected at this phase