from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from app.services.db_service import DatabaseService
from app.core.config import get_settings

settings = get_settings()
db_service = DatabaseService(
    host=settings.DB_HOST,
    user=settings.DB_USER,
    password=settings.DB_PASSWORD,
    database=settings.DB_NAME
)

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key header is missing"
        )
    if not db_service.verify_api_key(api_key_header):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API Key"
        )
    return api_key_header