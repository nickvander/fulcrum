import pytest
import base64
from src.core.encryption import EncryptionService, encryption_service

def test_encryption_decryption():
    """
    Test that a string can be encrypted and then decrypted back to the original.
    """
    plaintext = "super-secret-token-123"
    
    # Encrypt
    encrypted = encryption_service.encrypt(plaintext)
    assert encrypted != plaintext
    assert len(encrypted) > 0
    
    # Decrypt
    decrypted = encryption_service.decrypt(encrypted)
    assert decrypted == plaintext

def test_encryption_output_is_different_for_same_input():
    """
    Test that AES-GCM uses a random IV so that the same plaintext
    results in different ciphertexts.
    """
    plaintext = "consistent-secret"
    
    enc1 = encryption_service.encrypt(plaintext)
    enc2 = encryption_service.encrypt(plaintext)
    
    assert enc1 != enc2
    assert encryption_service.decrypt(enc1) == plaintext
    assert encryption_service.decrypt(enc2) == plaintext

def test_decryption_failure_with_bad_data():
    """
    Test that decryption fails gracefully with invalid base64 or corrupted data.
    """
    with pytest.raises(ValueError, match="Decryption failed"):
        encryption_service.decrypt("not-base64-at-all!")
        
    # Valid base64 but random data (too short to be IV + ciphertext)
    bad_data = base64.b64encode(b"too-short").decode()
    with pytest.raises(ValueError, match="Decryption failed"):
        encryption_service.decrypt(bad_data)

def test_custom_key():
    """
    Test that a custom key can be used.
    """
    custom_key = base64.b64encode(b"0" * 32).decode()
    service = EncryptionService(key=custom_key)
    
    plaintext = "data"
    encrypted = service.encrypt(plaintext)
    assert service.decrypt(encrypted) == plaintext
    
    # Ensure it fails with the singleton service key
    with pytest.raises(ValueError, match="Decryption failed"):
        encryption_service.decrypt(encrypted)

def test_key_length_validation():
    """
    Test that keys of incorrect length are rejected.
    """
    bad_key = base64.b64encode(b"short-key").decode()
    with pytest.raises(ValueError, match="Encryption key must be 32 bytes"):
        EncryptionService(key=bad_key)

def test_empty_string_handling():
    """
    Test that empty strings are handled correctly.
    """
    assert encryption_service.encrypt("") == ""
    assert encryption_service.decrypt("") == ""
