from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import Optional, Any

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

    APP_NAME: str = "Fulcrum API"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: Optional[str] = None
    REDIS_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    
    # Rate Limiting
    RATE_LIMIT_REDIS_URL: Optional[str] = None
    RATE_LIMIT_DEFAULT: str = "100/minute"
    # Magic-link endpoint limit (slowapi syntax). Tokens are 256-bit so this is
    # defence-in-depth against request floods / abuse, not brute-force.
    MAGIC_LINK_RATE_LIMIT: str = "10/minute"

    # CORS allow-list (FP-11). Comma-separated origins; EMPTY = no CORS middleware
    # (current behavior — browsers get no cross-origin grant). Set to the
    # storefront origin(s) in prod, e.g. "https://vendio.mx,https://www.vendio.mx".
    CORS_ALLOWED_ORIGINS: str = ""
    CORS_ALLOW_CREDENTIALS: bool = False

    # Inbound-webhook shared secret (FP-11, anti-forgery) for marketplaces that
    # do NOT sign their callbacks. When set, that webhook requires the token
    # (header "X-Webhook-Token" or query "?token="); UNSET = current behavior.
    # MercadoPago uses its own HMAC (MERCADOPAGO_WEBHOOK_SECRET) and is unaffected.
    ML_WEBHOOK_VERIFY_TOKEN: Optional[str] = None
    AMAZON_WEBHOOK_VERIFY_TOKEN: Optional[str] = None

    # Marketplace Encryption
    MARKETPLACE_ENCRYPTION_KEY: str

    # Amazon SP-API
    AMAZON_CLIENT_ID: Optional[str] = None
    AMAZON_CLIENT_SECRET: Optional[str] = None
    AMAZON_SELLER_ID: Optional[str] = "TEST_SELLER_ID"
    AMAZON_REDIRECT_URI: Optional[str] = "http://localhost:4200/marketplaces/amazon/callback"
    AMAZON_SANDBOX: bool = False

    # MercadoLibre Mexico
    ML_CLIENT_ID: Optional[str] = None
    ML_CLIENT_SECRET: Optional[str] = None
    ML_REDIRECT_URI: Optional[str] = "http://localhost:4200/marketplaces/mercadolibre/callback"

    # Mercado Pago Checkout API (Custom Checkout / Checkout Transparente).
    # MERCADOPAGO_ACCESS_TOKEN is the server-side secret used to call the
    # MP REST API. MERCADOPAGO_PUBLIC_KEY is the frontend SDK key (sent
    # to the browser). MERCADOPAGO_WEBHOOK_SECRET is the value of the
    # `x-signature` HMAC the MP dashboard generates when you enable
    # webhooks — we verify every incoming webhook against it. All three
    # default to None so a dev workspace renders without MP creds; the
    # connector falls back to its stub branch in that case.
    MERCADOPAGO_ACCESS_TOKEN: Optional[str] = None
    MERCADOPAGO_PUBLIC_KEY: Optional[str] = None
    MERCADOPAGO_WEBHOOK_SECRET: Optional[str] = None
    MERCADOPAGO_API_BASE_URL: str = "https://api.mercadopago.com"

    # Testing
    TESTING: bool = False

    # First superuser
    FIRST_SUPERUSER_EMAIL: str
    FIRST_SUPERUSER_PASSWORD: str

    # Allow individual DB components to be passed from Docker Compose
    POSTGRES_USER: str = "fulcrum"
    POSTGRES_PASSWORD: str = "fulcrum"
    POSTGRES_DB: str = "fulcrum"
    POSTGRES_HOST: str = "db"
    
    # AI 
    GEMINI_API_KEY: Optional[str] = None

    @model_validator(mode='before')
    def assemble_db_connection(cls, v: Any) -> Any:
        if isinstance(v, dict) and v.get("DATABASE_URL") is None:
            v["DATABASE_URL"] = (
                f"postgresql://{v.get('POSTGRES_USER')}:{v.get('POSTGRES_PASSWORD')}"
                f"@{v.get('POSTGRES_HOST')}/{v.get('POSTGRES_DB')}"
            )
        return v

settings = Settings()
