"""Tests for the customer self-service (FP-05) API.

Covers registration, the passwordless magic-link flow (reusing the
password-reset-token table), profile read/update, and address CRUD scoped to
the authenticated customer.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src import crud, models
from src.config import settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _register(client: TestClient, email: str, password: str = "Password123!") -> dict:
    return client.post(
        "/api/v1/customers/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Jane",
            "last_name": "Doe",
        },
    )


def _customer_headers(client: TestClient, db: Session, email: str) -> dict:
    """Sign a customer in via the magic-link flow and return auth headers."""
    user = crud.user.get_by_email(db, email=email)
    token = crud.password_reset_token.create_reset_token(db, user_id=user.id)
    r = client.post(
        "/api/v1/customers/magic-link/verify", json={"token": token.token}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
@pytest.mark.db
def test_register_success_creates_customer(client: TestClient, db: Session):
    r = _register(client, "newcustomer@example.com")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["email"] == "newcustomer@example.com"
    assert data["user_type"] == "customer"
    assert "hashed_password" not in data
    assert "password" not in data

    user = crud.user.get_by_email(db, email="newcustomer@example.com")
    assert user is not None
    assert user.user_type == "customer"


@pytest.mark.db
def test_register_duplicate_email_returns_409(client: TestClient):
    _register(client, "dupe@example.com")
    r = _register(client, "dupe@example.com")
    assert r.status_code == 409
    assert r.json()["code"] == "apiErrors.customer.emailExists"


# ---------------------------------------------------------------------------
# Magic link
# ---------------------------------------------------------------------------
@pytest.mark.db
def test_magic_link_request_existing_email_200(client: TestClient):
    _register(client, "magic-exists@example.com")
    r = client.post(
        "/api/v1/customers/magic-link/request",
        json={"email": "magic-exists@example.com"},
    )
    assert r.status_code == 200


@pytest.mark.db
def test_magic_link_request_unknown_email_200_no_leak(client: TestClient):
    r = client.post(
        "/api/v1/customers/magic-link/request",
        json={"email": "nobody-here@example.com"},
    )
    # No leak: same 200 + generic message as the existing-email case.
    assert r.status_code == 200
    assert "sign-in link" in r.json()["message"].lower()


@pytest.mark.db
def test_magic_link_verify_valid_token_returns_usable_jwt(
    client: TestClient, db: Session
):
    _register(client, "magic-valid@example.com")
    user = crud.user.get_by_email(db, email="magic-valid@example.com")
    token = crud.password_reset_token.create_reset_token(db, user_id=user.id)

    r = client.post(
        "/api/v1/customers/magic-link/verify", json={"token": token.token}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]

    # Round-trip: the JWT authenticates a get_current_customer route.
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    me = client.get("/api/v1/customers/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "magic-valid@example.com"


@pytest.mark.db
def test_magic_link_verify_invalid_token_4xx(client: TestClient):
    r = client.post(
        "/api/v1/customers/magic-link/verify", json={"token": "not-a-real-token"}
    )
    assert r.status_code == 400
    assert r.json()["code"] == "apiErrors.customer.magicLinkInvalid"


@pytest.mark.db
def test_magic_link_verify_used_token_4xx(client: TestClient, db: Session):
    _register(client, "magic-used@example.com")
    user = crud.user.get_by_email(db, email="magic-used@example.com")
    token = crud.password_reset_token.create_reset_token(db, user_id=user.id)

    first = client.post(
        "/api/v1/customers/magic-link/verify", json={"token": token.token}
    )
    assert first.status_code == 200
    # Single-use: second attempt fails.
    second = client.post(
        "/api/v1/customers/magic-link/verify", json={"token": token.token}
    )
    assert second.status_code == 400


@pytest.mark.db
def test_magic_link_verify_expired_token_4xx(client: TestClient, db: Session):
    from datetime import datetime, timedelta, timezone

    _register(client, "magic-expired@example.com")
    user = crud.user.get_by_email(db, email="magic-expired@example.com")
    token = crud.password_reset_token.create_reset_token(db, user_id=user.id)
    token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db.add(token)
    db.commit()

    r = client.post(
        "/api/v1/customers/magic-link/verify", json={"token": token.token}
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
@pytest.mark.db
def test_profile_requires_auth(client: TestClient):
    r = client.get("/api/v1/customers/me")
    assert r.status_code == 401


@pytest.mark.db
def test_profile_get_and_update(client: TestClient, db: Session):
    _register(client, "profile@example.com")
    headers = _customer_headers(client, db, "profile@example.com")

    got = client.get("/api/v1/customers/me", headers=headers)
    assert got.status_code == 200
    assert got.json()["first_name"] == "Jane"

    updated = client.patch(
        "/api/v1/customers/me",
        headers=headers,
        json={"first_name": "Janet", "phone": "555-1234"},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["first_name"] == "Janet"
    # phone now persists (users.phone column, migration a3f9c1d27b6e)...
    assert body["phone"] == "555-1234"
    # ...and round-trips on a fresh GET.
    refetched = client.get("/api/v1/customers/me", headers=headers)
    assert refetched.json()["phone"] == "555-1234"


@pytest.mark.db
def test_admin_cannot_use_customer_me(
    client: TestClient, test_admin_user: models.User
):
    """A non-customer (admin) is rejected by get_current_customer with 403.

    Expected behavior: /customers/me is customer-only; an authenticated admin
    receives 403 (authenticated but wrong user_type), not 200.
    """
    login = client.post(
        f"{settings.API_V1_STR}/users/login/access-token",
        data={"username": test_admin_user.email, "password": "TestPassword123!"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    r = client.get("/api/v1/customers/me", headers=headers)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Addresses
# ---------------------------------------------------------------------------
def _addr_payload() -> dict:
    return {
        "street": "Av. Reforma 100",
        "city": "Ciudad de Mexico",
        "state": "CDMX",
        "postal_code": "06000",
        "country": "MX",
    }


@pytest.mark.db
def test_addresses_require_auth(client: TestClient):
    assert client.get("/api/v1/customers/me/addresses").status_code == 401


@pytest.mark.db
def test_address_crud_roundtrip(client: TestClient, db: Session):
    _register(client, "addr@example.com")
    headers = _customer_headers(client, db, "addr@example.com")

    # Create
    created = client.post(
        "/api/v1/customers/me/addresses", headers=headers, json=_addr_payload()
    )
    assert created.status_code == 200, created.text
    addr_id = created.json()["id"]

    # List
    listed = client.get("/api/v1/customers/me/addresses", headers=headers)
    assert listed.status_code == 200
    assert any(a["id"] == addr_id for a in listed.json())

    # Update
    updated = client.put(
        f"/api/v1/customers/me/addresses/{addr_id}",
        headers=headers,
        json={"city": "Guadalajara"},
    )
    assert updated.status_code == 200
    assert updated.json()["city"] == "Guadalajara"

    # Delete
    deleted = client.delete(
        f"/api/v1/customers/me/addresses/{addr_id}", headers=headers
    )
    assert deleted.status_code == 200
    after = client.get("/api/v1/customers/me/addresses", headers=headers)
    assert all(a["id"] != addr_id for a in after.json())


@pytest.mark.db
def test_cannot_access_another_users_address(client: TestClient, db: Session):
    _register(client, "owner@example.com")
    _register(client, "intruder@example.com")
    owner_headers = _customer_headers(client, db, "owner@example.com")
    intruder_headers = _customer_headers(client, db, "intruder@example.com")

    created = client.post(
        "/api/v1/customers/me/addresses",
        headers=owner_headers,
        json=_addr_payload(),
    )
    addr_id = created.json()["id"]

    # Intruder cannot read/update/delete another user's address -> 404.
    upd = client.put(
        f"/api/v1/customers/me/addresses/{addr_id}",
        headers=intruder_headers,
        json={"city": "Monterrey"},
    )
    assert upd.status_code == 404
    assert upd.json()["code"] == "apiErrors.customer.addressNotFound"

    dele = client.delete(
        f"/api/v1/customers/me/addresses/{addr_id}", headers=intruder_headers
    )
    assert dele.status_code == 404
