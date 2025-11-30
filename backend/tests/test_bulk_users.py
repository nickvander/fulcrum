from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import io
from src import crud
from src.config import settings
from src.models.user import User

import pytest

def get_admin_headers(client: TestClient, admin_user: User) -> dict:
    login_data = {
        "username": admin_user.email,
        "password": "TestPassword123!"
    }
    r = client.post(f"{settings.API_V1_STR}/users/login/access-token", data=login_data)
    tokens = r.json()
    a_token = tokens["access_token"]
    return {"Authorization": f"Bearer {a_token}"}

@pytest.mark.db
def test_bulk_import_users_success(
    client: TestClient, test_admin_user: User, db: Session
) -> None:
    headers = get_admin_headers(client, test_admin_user)
    csv_content = """email,first_name,last_name,user_type
newuser1@example.com,John,Doe,employee
newuser2@example.com,Jane,Smith,customer
"""
    files = {
        "file": ("users.csv", io.BytesIO(csv_content.encode('utf-8')), "text/csv")
    }
    r = client.post(
        f"{settings.API_V1_STR}/bulk-users/bulk-import",
        headers=headers,
        files=files,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["created_users"]) == 2
    assert len(data["failed_users"]) == 0
    
    # Verify users in DB
    user1 = crud.user.get_by_email(db, email="newuser1@example.com")
    assert user1
    assert user1.first_name == "John"
    assert user1.user_type == "employee"
    
    user2 = crud.user.get_by_email(db, email="newuser2@example.com")
    assert user2
    assert user2.first_name == "Jane"
    assert user2.user_type == "customer"

@pytest.mark.db
def test_bulk_import_users_invalid_csv_format(
    client: TestClient, test_admin_user: User
) -> None:
    headers = get_admin_headers(client, test_admin_user)
    # Missing required column 'last_name'
    csv_content = """email,first_name,user_type
failuser@example.com,Fail,employee
"""
    files = {
        "file": ("users.csv", io.BytesIO(csv_content.encode('utf-8')), "text/csv")
    }
    r = client.post(
        f"{settings.API_V1_STR}/bulk-users/bulk-import",
        headers=headers,
        files=files,
    )
    assert r.status_code == 400
    assert "CSV must contain the following columns" in r.json()["detail"]

@pytest.mark.db
def test_bulk_import_users_duplicate_email(
    client: TestClient, test_admin_user: User, db: Session
) -> None:
    headers = get_admin_headers(client, test_admin_user)
    # Create a user first
    from src.schemas.user import UserCreate
    user_in = UserCreate(
        email="existing@example.com",
        password="Password123!",
        first_name="Existing",
        last_name="User",
        user_type="employee"
    )
    crud.user.create(db, obj_in=user_in)
    
    # Try to import same email
    csv_content = """email,first_name,last_name,user_type
existing@example.com,Duplicate,User,employee
"""
    files = {
        "file": ("users.csv", io.BytesIO(csv_content.encode('utf-8')), "text/csv")
    }
    r = client.post(
        f"{settings.API_V1_STR}/bulk-users/bulk-import",
        headers=headers,
        files=files,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["created_users"]) == 0
    assert len(data["failed_users"]) == 1
    assert data["failed_users"][0]["error"] == "User with this email already exists"

@pytest.mark.db
def test_bulk_import_users_invalid_file_type(
    client: TestClient, test_admin_user: User
) -> None:
    headers = get_admin_headers(client, test_admin_user)
    files = {
        "file": ("users.txt", io.BytesIO(b"some content"), "text/plain")
    }
    r = client.post(
        f"{settings.API_V1_STR}/bulk-users/bulk-import",
        headers=headers,
        files=files,
    )
    assert r.status_code == 400
    assert "Only CSV files are allowed" in r.json()["detail"]
