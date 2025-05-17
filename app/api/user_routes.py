# app/api/user_routes.py
from fastapi import APIRouter, HTTPException, Depends, Form
from app.services.db_service import DatabaseService
from app.api.auth import get_api_key
from app.core.config import get_settings
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()

db_service = DatabaseService(
    host=settings.DB_HOST,
    user=settings.DB_USER,
    password=settings.DB_PASSWORD,
    database=settings.DB_NAME
)

@router.post("/users")
async def create_user(
    userid: int = Form(...),
    username: str = Form(...),
    api_key: str = Depends(get_api_key)
):
    try:
        # Check if user already exists
        existing = db_service.get_user_by_userid_or_username(userid, username)
        if existing:
            raise HTTPException(status_code=400, detail="Usuario ya existe")

        # Create user
        user_id = db_service.create_user(userid, username)

        return {
            "status": "success",
            "message": "Usuario creado correctamente",
            "userid": userid,
            "username": username
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{userid}")
async def get_user(userid: str, api_key: str = Depends(get_api_key)):
    try:
        # Get user info
        user = db_service.get_user_by_userid(userid)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        user_id, username, created_at = user

        # Get all services for this user
        services = db_service.get_services_by_userid(userid)

        # Get all VMs for this user
        vms = db_service.get_vms_by_userid(userid)

        return {
            "userid": user_id,
            "username": username,
            "created_at": created_at,
            "services": services,
            "vms": vms
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        raise HTTPException(status_code=500, detail=str(e))