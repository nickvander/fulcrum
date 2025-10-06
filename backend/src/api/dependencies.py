"""
FastAPI dependencies for the Fulcrum application.
"""
from src.services.base import AIService
from src.services.dummy_ai_service import ai_service as dummy_ai_service

def get_ai_service() -> AIService:
    """
    Returns the currently configured AI service.
    
    In a real application, this would read from a config file
    to determine which AI service implementation to return.
    """
    return dummy_ai_service
