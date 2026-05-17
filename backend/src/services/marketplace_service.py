from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, Dict, Any, Type, TypeVar
import httpx
from sqlalchemy.orm import Session
from src.services.marketplaces.base import BaseMarketplaceConnector
from src.services.marketplaces.mercadolibre import MercadoLibreConnector
from src.services.marketplaces.amazon import AmazonConnector

T = TypeVar("T")


# How early before `expires_at` we proactively refresh a token. 5 minutes
# leaves enough headroom for a refresh round-trip plus the actual API call
# we're about to make, even on a slow network.
TOKEN_PRE_REFRESH_BUFFER = timedelta(minutes=5)


class ReauthorizationRequiredError(Exception):
    """
    Raised by `get_valid_access_token` when the credential cannot be
    refreshed (no refresh token, refresh API failed, or refresh response
    rejected). The corresponding MarketplaceCredential row is also marked
    with `needs_reauthorization=True` so the UI can surface the state
    without re-attempting the refresh.
    """

    def __init__(self, credential_id: int, marketplace_name: str, reason: str):
        self.credential_id = credential_id
        self.marketplace_name = marketplace_name
        self.reason = reason
        super().__init__(
            f"Reauthorization required for {marketplace_name} "
            f"credential #{credential_id}: {reason}"
        )


class MarketplaceService:
    """
    Orchestrator service that manages marketplace connections and operations.
    Uses the Strategy pattern to delegate to specific connectors.
    """

    def __init__(self):
        self._connectors: Dict[str, Type[BaseMarketplaceConnector]] = {
            "mercadolibre": MercadoLibreConnector,
            "amazon": AmazonConnector
        }
        self._instances: Dict[str, BaseMarketplaceConnector] = {}

    def get_connector(self, marketplace_name: str) -> BaseMarketplaceConnector:
        """
        Factory method to get the correct connector instance for a marketplace.
        """
        name = marketplace_name.lower()
        if name not in self._connectors:
            raise ValueError(f"Unsupported marketplace: {marketplace_name}")

        if name not in self._instances:
            self._instances[name] = self._connectors[name]()

        return self._instances[name]

    async def sync_product_inventory(self, db: Session, marketplace_name: str, external_id: str, quantity: int, access_token: str = None) -> bool:
        """
        Syncs inventory for a specific product listing on a marketplace.
        """
        connector = self.get_connector(marketplace_name)
        return await connector.sync_inventory(external_id, quantity, access_token=access_token)

    async def publish_listing(self, db: Session, marketplace_name: str, product_data: Dict[str, Any]) -> str:
        """
        Publishes a product to the specified marketplace.
        """
        connector = self.get_connector(marketplace_name)
        return await connector.publish_listing(product_data)

    async def get_valid_access_token(self, db: Session, credential_id: int) -> str:
        """
        Retrieves a valid access token, refreshing it proactively if it's
        within the pre-refresh window.

        Raises:
            ReauthorizationRequiredError: when the credential cannot be
                refreshed and the user must re-authorize. The credential
                row is updated with `needs_reauthorization=True` and the
                refresh error.
        """
        from src.crud.crud_marketplace_credential import marketplace_credential as crud_cred

        db_cred = crud_cred.get(db, id=credential_id)
        if not db_cred:
            raise ValueError(f"Credential with ID {credential_id} not found.")

        marketplace_name = db_cred.marketplace.name if db_cred.marketplace else "unknown"

        # If a previous refresh attempt failed and we haven't been re-authorized
        # since, surface the typed error immediately rather than spamming the
        # provider with another refresh.
        if db_cred.needs_reauthorization:
            raise ReauthorizationRequiredError(
                credential_id=db_cred.id,
                marketplace_name=marketplace_name,
                reason=db_cred.last_refresh_error or "credential previously marked for re-authorization",
            )

        # Wide enough buffer that the refresh round-trip itself doesn't run us
        # past the actual expiry.
        is_expired = False
        if db_cred.expires_at:
            is_expired = db_cred.expires_at <= (datetime.now(timezone.utc) + TOKEN_PRE_REFRESH_BUFFER)

        if not is_expired:
            return crud_cred.get_decrypted_access_token(db_cred)

        return await self._refresh_access_token(db, db_cred)

    async def force_refresh_access_token(self, db: Session, credential_id: int) -> str:
        """
        Force a token refresh regardless of expiry — used when an API call
        returns 401 even though the credential said it was still valid.
        """
        from src.crud.crud_marketplace_credential import marketplace_credential as crud_cred

        db_cred = crud_cred.get(db, id=credential_id)
        if not db_cred:
            raise ValueError(f"Credential with ID {credential_id} not found.")
        return await self._refresh_access_token(db, db_cred)

    async def call_with_401_retry(
        self,
        db: Session,
        credential_id: int,
        fn: Callable[[str], Awaitable[T]],
    ) -> T:
        """
        Run an async connector call (`fn(access_token)`) with automatic
        recovery from a stale-token 401.

        Flow:
        1. Resolve a valid token via `get_valid_access_token` (which may
           proactively refresh if we're inside the pre-refresh window).
        2. Invoke `fn(token)`.
        3. If `fn` raises `httpx.HTTPStatusError` with status 401, force-
           refresh the credential and retry `fn` once with the new token.
        4. If the retry also 401s — or `fn` raises any non-401 error —
           propagate.

        Why: `get_valid_access_token` uses local expiry metadata, but the
        provider can invalidate a token between calls (refresh-token
        rotation, manual revoke, password reset). Without this helper,
        every connector method has to duplicate the retry logic. Callers
        adopt this incrementally — sites that haven't migrated still work,
        they just don't self-heal on a server-side invalidation.

        Caller pattern:

            result = await marketplace_service.call_with_401_retry(
                db, credential_id,
                lambda token: connector.sync_inventory(ext_id, qty, access_token=token),
            )
        """
        token = await self.get_valid_access_token(db, credential_id)
        try:
            return await fn(token)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 401:
                raise
            # Token went stale between get_valid_access_token() and the
            # actual call — force a refresh and try again with the new one.
            new_token = await self.force_refresh_access_token(db, credential_id)
            return await fn(new_token)

    async def _refresh_access_token(self, db: Session, db_cred) -> str:
        """
        Internal helper. Executes the connector refresh, persists the new
        tokens, and either clears or sets the reauthorization flag.
        """
        from src.crud.crud_marketplace_credential import marketplace_credential as crud_cred
        from src.schemas.marketplace_credential import MarketplaceCredentialUpdate

        marketplace_name = db_cred.marketplace.name if db_cred.marketplace else "unknown"

        try:
            refresh_token = crud_cred.get_decrypted_refresh_token(db_cred)
        except Exception as exc:
            self._mark_reauth_required(db, db_cred, f"refresh_token unreadable: {exc}")
            raise ReauthorizationRequiredError(
                credential_id=db_cred.id,
                marketplace_name=marketplace_name,
                reason="refresh_token unreadable",
            )

        if not refresh_token:
            self._mark_reauth_required(db, db_cred, "no refresh_token stored")
            raise ReauthorizationRequiredError(
                credential_id=db_cred.id,
                marketplace_name=marketplace_name,
                reason="no refresh_token stored",
            )

        try:
            connector = self.get_connector(marketplace_name)
        except ValueError as exc:
            self._mark_reauth_required(db, db_cred, str(exc))
            raise ReauthorizationRequiredError(
                credential_id=db_cred.id,
                marketplace_name=marketplace_name,
                reason=str(exc),
            )

        try:
            new_tokens = await connector.refresh_token(refresh_token)
        except Exception as exc:
            self._mark_reauth_required(db, db_cred, f"refresh call failed: {exc}")
            raise ReauthorizationRequiredError(
                credential_id=db_cred.id,
                marketplace_name=marketplace_name,
                reason=f"refresh call failed: {exc}",
            )

        if not new_tokens or not new_tokens.get("access_token"):
            self._mark_reauth_required(db, db_cred, "refresh response missing access_token")
            raise ReauthorizationRequiredError(
                credential_id=db_cred.id,
                marketplace_name=marketplace_name,
                reason="refresh response missing access_token",
            )

        expires_at = None
        if "expires_in" in new_tokens:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=new_tokens["expires_in"])

        update_in = MarketplaceCredentialUpdate(
            access_token=new_tokens["access_token"],
            refresh_token=new_tokens.get("refresh_token") or refresh_token,
            expires_at=expires_at,
            needs_reauthorization=False,
            last_refresh_error=None,
        )
        crud_cred.update_with_encryption(db, db_obj=db_cred, obj_in=update_in)
        return new_tokens["access_token"]

    @staticmethod
    def _mark_reauth_required(db: Session, db_cred, reason: str) -> None:
        from src.crud.crud_marketplace_credential import marketplace_credential as crud_cred
        from src.schemas.marketplace_credential import MarketplaceCredentialUpdate

        crud_cred.update_with_encryption(
            db,
            db_obj=db_cred,
            obj_in=MarketplaceCredentialUpdate(
                needs_reauthorization=True,
                last_refresh_error=reason[:500],
            ),
        )


# Singleton instance
marketplace_service = MarketplaceService()
