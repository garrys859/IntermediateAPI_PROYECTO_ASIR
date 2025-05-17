import secrets
import string
import hashlib
from datetime import datetime, timedelta

def generate_api_key(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def validate_password(password: str, min_length: int = 8) -> bool:
    if len(password) < min_length:
        return False
    if not any(c.isdigit() for c in password):
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.islower() for c in password):
        return False
    special_chars = set("!@#$%^&*()_+-=[]{}|;:,.<>?")
    if not any(c in special_chars for c in password):
        return False
    return True

def create_api_key_with_expiry(name: str, days_valid: int = 90) -> dict:
    api_key = generate_api_key()
    expires_at = datetime.now() + timedelta(days=days_valid)
    return {
        "name": name,
        "key": api_key,
        "created_at": datetime.now(),
        "expires_at": expires_at,
        "is_active": "enabled"
    }