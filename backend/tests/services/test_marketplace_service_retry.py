"""Tests for MarketplaceService.call_with_401_retry — the helper that
self-heals connector calls when the provider invalidates a token
between get_valid_access_token() and the actual API call."""
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.services.marketplace_service import (
    MarketplaceService,
    ReauthorizationRequiredError,
)


def _make_401() -> httpx.HTTPStatusError:
    """Construct a real httpx 401 exception (the helper switches on the
    actual response status code, not the exception class)."""
    request = httpx.Request("GET", "https://example.com/api/foo")
    response = httpx.Response(401, request=request)
    return httpx.HTTPStatusError("401 Unauthorized", request=request, response=response)


def _make_500() -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.com/api/foo")
    response = httpx.Response(500, request=request)
    return httpx.HTTPStatusError("500 Server Error", request=request, response=response)


@pytest.mark.anyio
async def test_call_with_401_retry_happy_path_no_refresh():
    """When fn succeeds, no force-refresh is triggered and the result is
    returned as-is."""
    svc = MarketplaceService()
    db = MagicMock()
    fn = AsyncMock(return_value="result-OK")

    with patch.object(svc, "get_valid_access_token", AsyncMock(return_value="initial-token")), \
         patch.object(svc, "force_refresh_access_token", AsyncMock(return_value="new-token")) as mock_force:
        out = await svc.call_with_401_retry(db, credential_id=42, fn=fn)

    assert out == "result-OK"
    fn.assert_called_once_with("initial-token")
    mock_force.assert_not_called()


@pytest.mark.anyio
async def test_call_with_401_retry_refreshes_and_retries_on_401():
    """First fn invocation raises 401 → force_refresh is called → fn is
    invoked again with the new token → second result is returned."""
    svc = MarketplaceService()
    db = MagicMock()
    fn = AsyncMock(side_effect=[_make_401(), "result-after-refresh"])

    with patch.object(svc, "get_valid_access_token", AsyncMock(return_value="stale-token")), \
         patch.object(svc, "force_refresh_access_token", AsyncMock(return_value="fresh-token")) as mock_force:
        out = await svc.call_with_401_retry(db, credential_id=42, fn=fn)

    assert out == "result-after-refresh"
    assert fn.call_args_list[0].args == ("stale-token",)
    assert fn.call_args_list[1].args == ("fresh-token",)
    mock_force.assert_called_once_with(db, 42)


@pytest.mark.anyio
async def test_call_with_401_retry_propagates_second_401_as_reauth():
    """If both attempts 401, force_refresh succeeds but the second call
    still fails — the second 401 propagates. The caller can wrap to
    convert into a ReauthorizationRequiredError, or rely on
    force_refresh_access_token itself raising on its own failure path."""
    svc = MarketplaceService()
    db = MagicMock()
    fn = AsyncMock(side_effect=[_make_401(), _make_401()])

    with patch.object(svc, "get_valid_access_token", AsyncMock(return_value="token-1")), \
         patch.object(svc, "force_refresh_access_token", AsyncMock(return_value="token-2")):
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await svc.call_with_401_retry(db, credential_id=42, fn=fn)

    assert exc_info.value.response.status_code == 401
    assert fn.call_count == 2


@pytest.mark.anyio
async def test_call_with_401_retry_does_not_swallow_non_401_errors():
    """A 500 (or any non-401 HTTP error) must propagate without a
    refresh attempt — refreshing wouldn't help and would waste a
    provider API call."""
    svc = MarketplaceService()
    db = MagicMock()
    fn = AsyncMock(side_effect=_make_500())

    with patch.object(svc, "get_valid_access_token", AsyncMock(return_value="some-token")), \
         patch.object(svc, "force_refresh_access_token", AsyncMock()) as mock_force:
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await svc.call_with_401_retry(db, credential_id=42, fn=fn)

    assert exc_info.value.response.status_code == 500
    fn.assert_called_once()
    mock_force.assert_not_called()


@pytest.mark.anyio
async def test_call_with_401_retry_propagates_reauth_required_from_initial_token_resolution():
    """If get_valid_access_token itself raises ReauthorizationRequiredError
    (e.g. the credential was already marked), the helper propagates without
    calling fn at all."""
    svc = MarketplaceService()
    db = MagicMock()
    fn = AsyncMock()

    err = ReauthorizationRequiredError(
        credential_id=42, marketplace_name="MercadoLibre", reason="already marked",
    )
    with patch.object(svc, "get_valid_access_token", AsyncMock(side_effect=err)):
        with pytest.raises(ReauthorizationRequiredError):
            await svc.call_with_401_retry(db, credential_id=42, fn=fn)

    fn.assert_not_called()
