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
