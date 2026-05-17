"""End-to-end tests verifying users.py error responses use the new
LocalizedHTTPException wire shape {detail, code, params}.

Each test hits a distinct raise site so a future router-wide refactor
can't silently regress one branch. Pair test for each of the 10
distinct codes added in this migration.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src import models


@pytest.mark.db
def test_login_with_unknown_email_returns_localized_payload(client: TestClient):
    """Hits the /login/access-token 400 — every Mexican user's first failure path."""
    response = client.post(
        "/api/v1/users/login/access-token",
        data={"username": "nobody@example.com", "password": "anything"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body == {
        "detail": "Incorrect email or password",
        "code": "apiErrors.user.invalidCredentials",
        "params": {},
    }


@pytest.mark.db
def test_login_with_wrong_password_returns_localized_payload(
    client: TestClient, test_admin_user: models.User
):
    """Same code as unknown-email — both collapse to invalidCredentials to
    avoid leaking which half of the credential pair is wrong."""
    response = client.post(
        "/api/v1/users/login/access-token",
        data={"username": test_admin_user.email, "password": "WrongPassword123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "apiErrors.user.invalidCredentials"


@pytest.mark.db
def test_get_missing_user_returns_localized_notFound(
    client: TestClient, admin_headers: dict
):
    response = client.get("/api/v1/users/999999", headers=admin_headers)

    assert response.status_code == 404
    body = response.json()
    assert body == {
        "detail": "User not found",
        "code": "apiErrors.user.notFound",
        "params": {"id": 999999},
    }


@pytest.mark.db
def test_create_user_with_existing_email_returns_localized_alreadyExists(
    client: TestClient, admin_headers: dict, test_admin_user: models.User
):
    response = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={
            "email": test_admin_user.email,
            "password": "AnotherValidPass123!",
            "user_type": "employee",
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "apiErrors.user.alreadyExists"
    assert body["params"] == {"email": test_admin_user.email}
    assert body["detail"] == "The user with this username already exists in the system"


@pytest.mark.db
def test_non_admin_creating_admin_returns_localized_notEnoughPrivileges(
    client: TestClient, db: Session
):
    """Public POST /users/ with admin user_type and no auth header.
    The endpoint allows anonymous creates of regular users, but flags
    admin/superuser creates with 403."""
    response = client.post(
        "/api/v1/users/",
        json={
            "email": "should-not-exist@example.com",
            "password": "ValidPass123!",
            "user_type": "admin",
        },
    )

    assert response.status_code == 403
    body = response.json()
    assert body == {
        "detail": "The user doesn't have enough privileges",
        "code": "apiErrors.user.notEnoughPrivileges",
        "params": {},
    }


@pytest.mark.db
def test_change_password_wrong_current_returns_localized_incorrectPassword(
    client: TestClient, admin_headers: dict
):
    response = client.post(
        "/api/v1/users/change-password",
        headers=admin_headers,
        json={"current_password": "WrongCurrent!", "new_password": "NewValid123!"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "apiErrors.user.incorrectPassword"


@pytest.mark.db
def test_change_password_same_as_current_returns_localized_passwordSameAsCurrent(
    client: TestClient, admin_headers: dict
):
    response = client.post(
        "/api/v1/users/change-password",
        headers=admin_headers,
        json={"current_password": "TestPassword123!", "new_password": "TestPassword123!"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "apiErrors.user.passwordSameAsCurrent"


@pytest.mark.db
def test_admin_reset_password_for_missing_user_returns_localized_notFound(
    client: TestClient, admin_headers: dict
):
    """POST /{user_id}/admin-reset-password — admin-initiated password reset."""
    response = client.post(
        "/api/v1/users/999999/admin-reset-password",
        headers=admin_headers,
    )

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "apiErrors.user.notFound"
    assert body["params"] == {"id": 999999}


@pytest.mark.db
def test_reset_password_with_invalid_token_returns_localized_resetTokenInvalid(
    client: TestClient,
):
    """POST /password-reset with a bogus token. Public; no auth needed."""
    response = client.post(
        "/api/v1/users/password-reset",
        json={"token": "not-a-real-token", "new_password": "ValidNewPass123!"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "apiErrors.user.resetTokenInvalid"


@pytest.mark.db
def test_admin_cannot_deactivate_self_returns_localized_cannotDeactivateSelf(
    client: TestClient, admin_headers: dict, test_admin_user: models.User
):
    response = client.delete(
        f"/api/v1/users/{test_admin_user.id}",
        headers=admin_headers,
    )

    assert response.status_code == 400
    body = response.json()
    assert body == {
        "detail": "You cannot deactivate your own account",
        "code": "apiErrors.user.cannotDeactivateSelf",
        "params": {},
    }


@pytest.mark.db
def test_admin_cannot_permanently_delete_self_returns_localized_cannotDeleteSelf(
    client: TestClient, admin_headers: dict, test_admin_user: models.User
):
    response = client.delete(
        f"/api/v1/users/{test_admin_user.id}/permanent",
        headers=admin_headers,
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "apiErrors.user.cannotDeleteSelf"
