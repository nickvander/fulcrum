import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from src.config import settings

class EncryptionService:
    """
    Service for AES-256-GCM authenticated encryption.
    Used for securing sensitive marketplace tokens.
    """

    def __init__(self, key: str = None):
        # Key must be 32 bytes for AES-256
        raw_key = key or settings.MARKETPLACE_ENCRYPTION_KEY
        if isinstance(raw_key, str):
            # Expecting a base64 encoded key for ease of storage in .env
            try:
                self.key = base64.b64decode(raw_key)
            except Exception:
                self.key = raw_key.encode()
        else:
            self.key = raw_key
        
        if len(self.key) != 32:
            raise ValueError("Encryption key must be 32 bytes (256 bits).")
        
        self.aesgcm = AESGCM(self.key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypts a string and returns a base64 encoded string containing IV + Tag + Ciphertext.
        """
        if not plaintext:
            return ""
        
        # 12 bytes is standard for AES-GCM IV
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext.encode(), None)
        
        # Combine nonce and ciphertext
        combined = nonce + ciphertext
        return base64.b64encode(combined).decode('utf-8')

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypts a base64 encoded string.
        """
        if not encrypted_data:
            return ""
        
        try:
            combined = base64.b64decode(encrypted_data)
            nonce = combined[:12]
            ciphertext = combined[12:]
            
            decrypted = self.aesgcm.decrypt(nonce, ciphertext, None)
            return decrypted.decode('utf-8')
        except Exception as e:
            # Re-raise as a generic DecryptionError or just ValueError
            raise ValueError(f"Decryption failed: {str(e)}")

# Singleton instance using app settings
encryption_service = EncryptionService()
