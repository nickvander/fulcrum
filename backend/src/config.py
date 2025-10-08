from pydantic_settings import BaseSettings
from pydantic import model_validator, Field
from typing import Optional, Any

class Settings(BaseSettings):
    APP_NAME: str = "Fulcrum API"
    DATABASE_URL: Optional[str] = None
    REDIS_URL: str
    SECRET_KEY: str

    # Allow individual DB components to be passed from Docker Compose
    POSTGRES_USER: str = Field("fulcrum", env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field("fulcrum", env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field("fulcrum", env="POSTGRES_DB")
    POSTGRES_HOST: str = Field("db", env="POSTGRES_HOST")

    @model_validator(mode='before')
    def assemble_db_connection(cls, v: Any) -> Any:
        if isinstance(v, dict) and v.get("DATABASE_URL") is None:
            v["DATABASE_URL"] = (
                f"postgresql://{v.get('POSTGRES_USER')}:{v.get('POSTGRES_PASSWORD')}"
                f"@{v.get('POSTGRES_HOST')}/{v.get('POSTGRES_DB')}"
            )
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
