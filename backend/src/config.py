from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Fulcrum API"
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()
