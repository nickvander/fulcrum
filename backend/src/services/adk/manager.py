"""
ADK Manager Service.

Handles initialization of AI agents and model clients using config from StoreSettings.
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from src.models.store_settings import StoreSettings

class ADKManager:
    """
    Manages AI Agent configuration and initialization.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = self._get_store_settings()

    def _get_store_settings(self) -> Optional[StoreSettings]:
        """Retrieve the single store settings record."""
        return self.db.query(StoreSettings).first()

    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Retrieve decrypted API key for a provider.
        """
        if not self.settings:
            return None
        
        from src.core.encryption import encryption_service
        
        provider = provider.lower()
        encrypted_key = None
        
        if provider == "google":
            encrypted_key = self.settings.ai_google_api_key
        elif provider == "openai":
            encrypted_key = self.settings.ai_openai_api_key
        elif provider == "anthropic":
            encrypted_key = self.settings.ai_anthropic_api_key
        elif provider == "qwen":
            encrypted_key = self.settings.ai_qwen_api_key
            
        if encrypted_key:
            return encryption_service.decrypt(encrypted_key)
            
        return None

    def is_configured(self, provider: str) -> bool:
        """Check if a provider has an API key."""
        return bool(self.get_api_key(provider))

    def get_active_config(self) -> Dict[str, Any]:
        """
        Return configuration for the active AI model.
        Respects 'ai_provider' and 'ai_model' settings.
        """
        if not self.settings:
             raise ValueError("Store settings not found.")

        # Check if enabled
        if not self.settings.ai_enabled:
             raise ValueError("AI features are disabled in Settings.")

        provider = self.settings.ai_provider or "google"
        model_override = self.settings.ai_model
        
        # Determine defaults
        defaults = {
            "google": "gemini-3-flash-preview",
            "openai": "gpt-4o",
            "anthropic": "claude-3-opus-20240229",
            "qwen": "qwen-plus" # Example, maps to model name
        }
        
        default_model = defaults.get(provider, "gemini-3-flash-preview")
        model = model_override if model_override else default_model
        
        api_key = self.get_api_key(provider)
        
        if not api_key:
             # Fallback logic could go here, but for now strict
             raise ValueError(f"AI Provider '{provider}' is selected but not configured (missing API Key).")
             
        return {
            "provider": provider,
            "model": model,
            "api_key": api_key
        }
