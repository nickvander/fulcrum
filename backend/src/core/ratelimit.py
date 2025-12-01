from slowapi import Limiter
from slowapi.util import get_remote_address
from src.config import settings

# Initialize Limiter
limiter = Limiter(
    key_func=get_remote_address, 
    default_limits=[settings.RATE_LIMIT_DEFAULT], 
    storage_uri=settings.RATE_LIMIT_REDIS_URL or settings.REDIS_URL,
    enabled=not settings.TESTING
)
