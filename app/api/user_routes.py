from fastapi import APIRouter, HTTPException, Depends, Form
from app.services.db_service import DatabaseService
from app.api.auth import get_api_key
from app.core.config import get_settings

router = APIRouter()
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
    existing = db_service.get_user_by_userid_or_username(userid, username)
    if existing:
        raise HTTPException(status_code=400, detail="Usuario ya existe")
    db_service.create_user(userid, username)
    return {
        "status": "success",
        "message": "Usuario creado correctamente",
        "userid": userid,
        "username": username
    }

@router.get("/users/{userid}")
async def get_user(userid: str, api_key: str = Depends(get_api_key)):
    user = db_service.get_user_by_userid(userid)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user_id, username, created_at = user
    services = db_service.get_services_by_userid(userid)
    vms = db_service.get_vms_by_userid(userid)
    return {
        "userid": user_id,
        "username": username,
        "created_at": created_at,
        "services": services,
        "vms": vms
    }