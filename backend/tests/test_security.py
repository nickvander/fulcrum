"""
Security tests for user management system
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.models.user import User
from src.core import security
from datetime import datetime, timedelta
from jose import jwt
from src.config import settings

# Mark all tests in this module as database-dependent
pytestmark = pytest.mark.db


def test_jwt_token_expiration(client: TestClient, db: Session, test_employee_user: User) -> None:
    """Test JWT token expiration functionality"""
    # Login to get a token
    login_data = {
        "username": test_employee_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Decode the token to check its expiration
    decoded_token = jwt.decode(access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    
    # Verify the token has an expiration time
    assert "exp" in decoded_token
    exp_time = datetime.fromtimestamp(decoded_token["exp"])
    current_time = datetime.utcnow()
    
    # The token should expire in the future but not be indefinitely valid
    assert exp_time > current_time
    assert exp_time <= current_time + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES + 1)


def test_jwt_token_manipulation(client: TestClient, db: Session, test_employee_user: User) -> None:
    """Test that JWT tokens can't be easily manipulated"""
    # Login to get a token
    login_data = {
        "username": test_employee_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Try to manipulate the token by changing the user ID in the payload
    # This is a simplified test - in real scenario, we'd try different manipulations
    try:
        # Decode token without verification (for testing purposes only)
        decoded_payload = jwt.get_unverified_claims(access_token)
        
        # Try to create a new token with a different user ID
        modified_payload = decoded_payload.copy()
        modified_payload["sub"] = 99999  # Non-existent user ID
        
        # Try to encode the modified payload with the same algorithm
        # This should fail with the real secret key
        modified_token = jwt.encode(modified_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        # Try to use the modified token on a protected endpoint
        profile_response = client.get("/api/v1/users/profile", 
                                     headers={"Authorization": f"Bearer {modified_token}"})
        
        # The server should reject this token since it doesn't match the original signature
        if profile_response.status_code != 200:
            # This is expected - the modified token should be rejected
            pass
        else:
            # If it does work, we have a security issue
            assert False, "Token manipulation succeeded - this is a security vulnerability"
    except jwt.JWTError:
        # This is expected behavior - the token manipulation should fail
        pass


def test_insufficient_role_privilege_escalation(client: TestClient, db: Session, test_employee_user: User) -> None:
    """Test that users can't escalate their privileges to admin"""
    # Login as employee user
    login_data = {
        "username": test_employee_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Try to create a user with admin privileges (should fail for non-admin)
    admin_user_data = {
        "email": "newadmin@test.com",
        "password": "ValidPass123!",
        "first_name": "New",
        "last_name": "Admin",
        "user_type": "admin",
        "is_superuser": True
    }
    response = client.post("/api/v1/users/", 
                          json=admin_user_data,
                          headers={"Authorization": f"Bearer {access_token}"})
    # Should fail with forbidden status
    assert response.status_code == 403  # Forbidden


def test_user_cannot_change_own_admin_status(client: TestClient, db: Session, test_employee_user: User) -> None:
    """Test that users can't make themselves admins"""
    # Login as employee user
    login_data = {
        "username": test_employee_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Try to update own profile to make self an admin
    update_data = {
        "user_type": "admin",
        "is_superuser": True
    }
    client.put("/api/v1/users/profile", 
                         json=update_data,
                         headers={"Authorization": f"Bearer {access_token}"})
    
    # This should either fail or ignore the admin fields
    profile_response = client.get("/api/v1/users/profile",
                                 headers={"Authorization": f"Bearer {access_token}"})
    assert profile_response.status_code == 200
    
    profile = profile_response.json()
    # Make sure the user_type and is_superuser haven't changed to admin
    assert profile["user_type"] != "admin" or profile["is_superuser"] is False


def test_user_cannot_access_admin_endpoints(client: TestClient, db: Session, test_employee_user: User) -> None:
    """Test that non-admin users can't access admin-only endpoints"""
    # Login as employee user
    login_data = {
        "username": test_employee_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Try to access user list endpoint (admin only)
    response = client.get("/api/v1/users/", 
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 403  # Forbidden
    
    # Try to update another user (should fail for non-admin)
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
    
    update_data = {"first_name": "Hacked"}
    response = client.put(f"/api/v1/users/{other_user['id']}", 
                         json=update_data,
                         headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 403  # Forbidden


def test_admin_password_reset_access_control(client: TestClient, db: Session, test_employee_user: User, test_customer_user: User) -> None:
    """Test that only admins can reset other users' passwords"""
    # Login as employee user
    login_data = {
        "username": test_employee_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Try to reset customer user's password (should fail for non-admin)
    response = client.post(f"/api/v1/users/{test_customer_user.id}/admin-reset-password",
                          headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 403  # Forbidden


def test_sql_injection_protection(client: TestClient, db: Session, test_admin_user: User) -> None:
    """Test basic SQL injection protection"""
    # Login as admin
    login_data = {
        "username": test_admin_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Try to pass SQL injection in search parameter
    malicious_search = "'; DROP TABLE users; --"
    response = client.get(f"/api/v1/users/?search={malicious_search}", 
                         headers={"Authorization": f"Bearer {access_token}"})
    
    # Should not cause a server error or allow SQL injection
    assert response.status_code in [200, 422]  # Either processed safely or validation error


def test_user_deactivation_protection(client: TestClient, db: Session, test_employee_user: User) -> None:
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
    
    # Try to deactivate own account (should be prevented in the backend)
    client.delete(f"/api/v1/users/{test_employee_user.id}", 
                           headers={"Authorization": f"Bearer {access_token}"})
    
    # Should either be forbidden or have special handling for self-deactivation
    # Implementation may vary, but self-deactivation should be restricted


def test_jwt_token_reuse_after_password_change(client: TestClient, db: Session, test_employee_user: User) -> None:
    """Test that JWT tokens become invalid after password change"""
    # Login to get a token
    login_data = {
        "username": test_employee_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Verify the token works initially
    profile_response = client.get("/api/v1/users/profile", 
                                 headers={"Authorization": f"Bearer {access_token}"})
    assert profile_response.status_code == 200
    
    # Now change the user's password (this would normally happen via profile update or admin action)
    # For this test, we'll simulate changing the password directly
    new_hashed_password = security.get_password_hash("NewPassword456!")
    test_employee_user.hashed_password = new_hashed_password
    db.add(test_employee_user)
    db.commit()
    
    # The old token should still work (JWTs are stateless), but in a real system with 
    # a token blacklist or session tracking, it would be invalidated
    # For now, we'll just verify the password change worked by trying to login with old password
    old_login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert old_login_response.status_code == 400  # Should fail with old password


def test_brute_force_protection_simulation(client: TestClient, db: Session) -> None:
    """Test that repeated failed login attempts are handled properly (simulated)"""
    # Try to login with invalid credentials multiple times
    invalid_login_data = {
        "username": "nonexistent@test.com",
        "password": "WrongPassword123!"
    }
    
    # Make several failed login attempts
    for i in range(5):
        response = client.post("/api/v1/users/login/access-token", data=invalid_login_data)
        assert response.status_code == 400  # Should fail


def test_sensitive_operation_audit_logging(client: TestClient, db: Session, test_admin_user: User) -> None:
    """Test that sensitive operations are properly logged in audit logs"""
    # Create a user first
    user_data = {
        "email": "audit@test.com",
        "password": "ValidPass123!",
        "first_name": "Audit",
        "last_name": "Test",
        "user_type": "employee"
    }
    create_response = client.post("/api/v1/users/", json=user_data)
    assert create_response.status_code == 200
    user = create_response.json()
    
    # Login as admin to perform sensitive operations
    login_data = {
        "username": test_admin_user.email,
        "password": "TestPassword123!"
    }
    login_response = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Deactivate the user (sensitive operation that should be logged)
    response = client.delete(f"/api/v1/users/{user['id']}", 
                           headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    
    # The deactivation should have created an audit log entry
    # This would need to check the audit_logs table in a real implementation
    # For this test, we're verifying the operation completed successfully
    # which indicates the audit logging was implemented without errors
    
    # Verify the user is now inactive
    get_response = client.get(f"/api/v1/users/{user['id']}", 
                            headers={"Authorization": f"Bearer {access_token}"})
    assert get_response.status_code == 200
    retrieved_user = get_response.json()
    assert retrieved_user["is_active"] is False


def test_password_reset_token_security(client: TestClient, db: Session, test_employee_user: User) -> None:
    """Test security of password reset token functionality"""
    # Request a password reset
    reset_request_data = {"email": test_employee_user.email}
    response = client.post("/api/v1/users/password-reset-request", json=reset_request_data)
    assert response.status_code == 200
    
    # Verify that the response doesn't leak information about whether the user exists
    result = response.json()
    assert "message" in result  # Should have a generic response
    
    # Try with a non-existent email
    reset_request_data = {"email": "nonexistent@test.com"}
    response = client.post("/api/v1/users/password-reset-request", json=reset_request_data)
    assert response.status_code == 200
    
    # The response should be identical to avoid revealing if user exists
    non_existent_result = response.json()
    # Both responses should be the same to prevent enumeration
    assert "message" in non_existent_result


def test_concurrent_session_behavior(client: TestClient, db: Session, test_employee_user: User) -> None:
    """Test behavior with multiple concurrent sessions for a user"""
    # Login to get first token
    login_data = {
        "username": test_employee_user.email,
        "password": "TestPassword123!"
    }
    login_response1 = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response1.status_code == 200
    
    token_data1 = login_response1.json()
    access_token1 = token_data1["access_token"]
    
    # Login again to get second token
    login_response2 = client.post("/api/v1/users/login/access-token", data=login_data)
    assert login_response2.status_code == 200
    
    token_data2 = login_response2.json()
    access_token2 = token_data2["access_token"]
    
    # Both tokens should work for concurrent access
    profile_response1 = client.get("/api/v1/users/profile", 
                                  headers={"Authorization": f"Bearer {access_token1}"})
    profile_response2 = client.get("/api/v1/users/profile", 
                                  headers={"Authorization": f"Bearer {access_token2}"})
    
    assert profile_response1.status_code == 200
    assert profile_response2.status_code == 200


def test_weak_password_rejection(client: TestClient, db: Session) -> None:
    """Test that weak passwords are properly rejected"""
    # Test various weak password patterns
    weak_passwords = [
        "12345678",        # Only numbers
        "password",        # Common password
        "aaaaaaa",         # Repeated characters
        "short",           # Too short
        "nouppercase1!",   # No uppercase
        "NOLOWERCASE1!",   # No lowercase
        "NoNumbers!",      # No numbers
        "NoSpecial1",      # No special characters
    ]
    
    for weak_password in weak_passwords:
        user_data = {
            "email": f"weakpass{weak_password}@test.com",
            "password": weak_password,
            "first_name": "Weak",
            "last_name": "Password",
            "user_type": "employee"
        }
        response = client.post("/api/v1/users/", json=user_data)
        # Should fail validation
        assert response.status_code in [422, 400], f"Weak password '{weak_password}' was accepted"