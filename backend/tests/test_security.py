from src.core.security import verify_password, get_password_hash

def test_password_hashing():
    """
    Tests that the password hashing and verification functions work correctly.
    This is a true unit test with no database or client dependency.
    """
    password = "mysecretpassword"
    
    # Hash the password
    hashed_password = get_password_hash(password)
    
    # Verify that the plain password matches the hash
    assert verify_password(password, hashed_password)
    
    # Verify that a wrong password does not match
    assert not verify_password("wrongpassword", hashed_password)
    
    # Verify that the hash is a string and not empty
    assert isinstance(hashed_password, str)
    assert hashed_password is not None
