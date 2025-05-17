# /app/core/security.py
import secrets
import string
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

def generate_api_key(length: int = 32) -> str:
    """
    Genera una API key aleatoria.

    Args:
        length: Longitud de la API key

    Returns:
        Una API key aleatoria
    """
    alphabet = string.ascii_letters + string.digits
    api_key = ''.join(secrets.choice(alphabet) for _ in range(length))
    return api_key

def hash_password(password: str) -> str:
    """
    Genera un hash seguro de una contraseña.

    Args:
        password: La contraseña a hashear

    Returns:
        El hash de la contraseña
    """
    return hashlib.sha256(password.encode()).hexdigest()

def validate_password(password: str, min_length: int = 8) -> bool:
    """
    Valida que una contraseña cumpla con los requisitos mínimos de seguridad.

    Args:
        password: La contraseña a validar
        min_length: Longitud mínima de la contraseña

    Returns:
        True si la contraseña es válida, False en caso contrario
    """
    if len(password) < min_length:
        return False

    # Verificar que la contraseña contenga al menos un número
    if not any(c.isdigit() for c in password):
        return False

    # Verificar que la contraseña contenga al menos una letra mayúscula
    if not any(c.isupper() for c in password):
        return False

    # Verificar que la contraseña contenga al menos una letra minúscula
    if not any(c.islower() for c in password):
        return False

    # Verificar que la contraseña contenga al menos un carácter especial
    special_chars = set("!@#$%^&*()_+-=[]{}|;:,.<>?")
    if not any(c in special_chars for c in password):
        return False

    return True

def create_api_key_with_expiry(name: str, days_valid: int = 90) -> dict:
    """
    Crea una nueva API key con fecha de expiración.

    Args:
        name: Nombre para identificar la API key
        days_valid: Días de validez de la API key

    Returns:
        Un diccionario con la información de la API key
    """
    api_key = generate_api_key()
    expires_at = datetime.now() + timedelta(days=days_valid)

    return {
        "name": name,
        "key": api_key,
        "created_at": datetime.now(),
        "expires_at": expires_at,
        "is_active": "enabled"
    }