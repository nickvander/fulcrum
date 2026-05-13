"""
Tests for OAuth token-refresh hardening: pre-refresh buffer, typed
ReauthorizationRequiredError, and the needs_reauthorization flag lifecycle
on MarketplaceCredential.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from src.crud.crud_marketplace import marketplace as crud_m
from src.crud.crud_marketplace_credential import marketplace_credential as crud_cred
from src.schemas.marketplace import MarketplaceCreate
from src.schemas.marketplace_credential import MarketplaceCredentialCreate
from src.services.marketplace_service import (
    ReauthorizationRequiredError,
    TOKEN_PRE_REFRESH_BUFFER,
    marketplace_service,
)


pytestmark = [pytest.mark.db, pytest.mark.anyio]


def _make_credential(db, user, *, name="MercadoLibre", expires_at=None, refresh_token="valid-refresh"):
    marketplace = crud_m.create(
        db, obj_in=MarketplaceCreate(name=name, api_base_url="https://api.example.com")
    )
    cred_in = MarketplaceCredentialCreate(
        marketplace_id=marketplace.id,
        access_token="current-access",
        refresh_token=refresh_token,
        expires_at=expires_at,
    )
    return crud_cred.create_with_owner(db, obj_in=cred_in, user_id=user.id)


async def test_token_within_buffer_does_not_refresh(db, test_admin_user):
    """If expires_at is comfortably in the future, do not call refresh."""
    db_cred = _make_credential(
        db,
        test_admin_user,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
    )
    with patch(
        "src.services.marketplace_service.MarketplaceService.get_connector"
    ) as mock_get:
        token = await marketplace_service.get_valid_access_token(db, db_cred.id)
    mock_get.assert_not_called()
    assert token == "current-access"


async def test_token_inside_pre_refresh_window_triggers_refresh(db, test_admin_user):
    """Tokens that expire within the buffer window should refresh proactively."""
    # Expires in 2 minutes — that's inside the 5-minute pre-refresh buffer.
    db_cred = _make_credential(
        db,
        test_admin_user,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=2),
    )
    assert TOKEN_PRE_REFRESH_BUFFER >= timedelta(minutes=2)

    with patch(
        "src.services.marketplace_service.MarketplaceService.get_connector"
    ) as mock_get:
        mock_connector = AsyncMock()
        mock_connector.refresh_token.return_value = {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "expires_in": 3600,
        }
        mock_get.return_value = mock_connector
        token = await marketplace_service.get_valid_access_token(db, db_cred.id)

    assert token == "new-access"
    mock_connector.refresh_token.assert_awaited_once()
    db.refresh(db_cred)
    assert db_cred.needs_reauthorization is False
    assert db_cred.last_refresh_error is None


async def test_refresh_failure_marks_credential_and_raises_typed_error(
    db, test_admin_user
):
    db_cred = _make_credential(
        db,
        test_admin_user,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )

    with patch(
        "src.services.marketplace_service.MarketplaceService.get_connector"
    ) as mock_get:
        mock_connector = AsyncMock()
        mock_connector.refresh_token.side_effect = RuntimeError("invalid_grant")
        mock_get.return_value = mock_connector

        with pytest.raises(ReauthorizationRequiredError) as exc_info:
            await marketplace_service.get_valid_access_token(db, db_cred.id)

    assert "invalid_grant" in exc_info.value.reason
    assert exc_info.value.credential_id == db_cred.id

    db.refresh(db_cred)
    assert db_cred.needs_reauthorization is True
    assert db_cred.last_refresh_error is not None
    assert "invalid_grant" in db_cred.last_refresh_error


async def test_credential_already_marked_short_circuits(db, test_admin_user):
    """Once needs_reauthorization is set, do not retry; raise immediately."""
    db_cred = _make_credential(
        db,
        test_admin_user,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    # Manually mark it as needing re-auth.
    db_cred.needs_reauthorization = True
    db_cred.last_refresh_error = "previously denied"
    db.commit()
    db.refresh(db_cred)

    with patch(
        "src.services.marketplace_service.MarketplaceService.get_connector"
    ) as mock_get:
        with pytest.raises(ReauthorizationRequiredError):
            await marketplace_service.get_valid_access_token(db, db_cred.id)
    mock_get.assert_not_called()


async def test_successful_refresh_clears_prior_reauth_flag(db, test_admin_user):
    """A successful refresh after the user re-authorizes should clear the flag."""
    # Start in a state where the user manually re-authorized — meaning a fresh
    # token has been written but the flag may still need to flip back.
    db_cred = _make_credential(
        db,
        test_admin_user,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )

    with patch(
        "src.services.marketplace_service.MarketplaceService.get_connector"
    ) as mock_get:
        mock_connector = AsyncMock()
        mock_connector.refresh_token.return_value = {
            "access_token": "refreshed",
            "refresh_token": "new-refresh",
            "expires_in": 3600,
        }
        mock_get.return_value = mock_connector
        await marketplace_service.get_valid_access_token(db, db_cred.id)

    db.refresh(db_cred)
    assert db_cred.needs_reauthorization is False
    assert db_cred.last_refresh_error is None


async def test_refresh_response_missing_access_token_marks_reauth(db, test_admin_user):
    db_cred = _make_credential(
        db,
        test_admin_user,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )

    with patch(
        "src.services.marketplace_service.MarketplaceService.get_connector"
    ) as mock_get:
        mock_connector = AsyncMock()
        # Provider responded but didn't include a new access token.
        mock_connector.refresh_token.return_value = {"refresh_token": "still-here"}
        mock_get.return_value = mock_connector

        with pytest.raises(ReauthorizationRequiredError):
            await marketplace_service.get_valid_access_token(db, db_cred.id)

    db.refresh(db_cred)
    assert db_cred.needs_reauthorization is True


async def test_force_refresh_bypasses_expiry_check(db, test_admin_user):
    """`force_refresh_access_token` always calls the connector even when the
    stored expiry is still in the future. Use case: API call returned 401."""
    db_cred = _make_credential(
        db,
        test_admin_user,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=3),
    )

    with patch(
        "src.services.marketplace_service.MarketplaceService.get_connector"
    ) as mock_get:
        mock_connector = AsyncMock()
        mock_connector.refresh_token.return_value = {
            "access_token": "force-refreshed",
            "refresh_token": "new-refresh",
            "expires_in": 3600,
        }
        mock_get.return_value = mock_connector
        token = await marketplace_service.force_refresh_access_token(db, db_cred.id)

    assert token == "force-refreshed"
    mock_connector.refresh_token.assert_awaited_once()
