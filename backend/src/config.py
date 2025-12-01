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

    @model_validator(mode='before')
    def assemble_db_connection(cls, v: Any) -> Any:
        if isinstance(v, dict) and v.get("DATABASE_URL") is None:
            v["DATABASE_URL"] = (
                f"postgresql://{v.get('POSTGRES_USER')}:{v.get('POSTGRES_PASSWORD')}"
                f"@{v.get('POSTGRES_HOST')}/{v.get('POSTGRES_DB')}"
            )
        return v

settings = Settings()
