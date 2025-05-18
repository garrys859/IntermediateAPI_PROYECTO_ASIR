from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from uuid import uuid4
import os
import tempfile
import subprocess

from app.core.config import get_settings
from app.services.docker_service import DockerService
from app.api.auth import get_api_key
from app.models import Service, ServiceCreate, ServicioTipo, ServiceAction

router = APIRouter(
    dependencies=[Depends(get_api_key)]
)

settings = get_settings()
docker_service = DockerService()

@router.post("/service", response_model=Service, status_code=status.HTTP_201_CREATED)
async def create_service(
    id_user: int = Form(...),
    tipo_servicio: ServicioTipo = Form(...),
    nombre_servicio: str = Form(...),
    archivo: UploadFile = File(None),
    git_repo_url: str = Form(None)
):
    zip_path = None
    try:
        if archivo:
            if not archivo.filename.endswith(".zip"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File must be a .zip"
                )
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            temp_file.close()
            with open(temp_file.name, "wb") as f:
                f.write(await archivo.read())
            zip_path = temp_file.name

        result = docker_service.create_service(
            userid=id_user,
            webname=nombre_servicio,
            tipo_servicio=tipo_servicio.value,
            zip_path=zip_path
        )

        if git_repo_url and git_repo_url.strip():
            try:
                user = docker_service.db_service.get_user_by_userid_or_username(id_user, "")
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Username not found for the given user ID"
                    )
                _, username = user
                project_path = f"/srv/users/{username}/{nombre_servicio}/data"
                os.makedirs(project_path, exist_ok=True)
                result_clone = subprocess.run(
                    ["git", "clone", git_repo_url, project_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if result_clone.returncode != 0:
                    raise Exception(f"Git clone failed: {result_clone.stderr}")
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to clone git repository: {str(e)}"
                )

        service_create = ServiceCreate(
            id_user=id_user,
            tipo_servicio=[tipo_servicio],
            nombre_servicio=nombre_servicio
        )
        service_id = str(uuid4())
        return Service(id_service=service_id, info=service_create, status=result["status"])

    except Exception as e:
        if zip_path and os.path.exists(zip_path):
            os.unlink(zip_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating service: {str(e)}"
        )

@router.get("/service/{service_id}", response_model=Service)
async def get_service(service_id: str):
    try:
        query = """
        SELECT ds.userid, ds.webname, ds.webtype_id, ds.status, wt.name as webtype_name
        FROM docker_services ds
        JOIN webtypes wt ON ds.webtype_id = wt.id
        WHERE ds.id = %s
        """
        result = docker_service.db_service.fetch_one(query, (service_id,))
        if not result:
            raise HTTPException(status_code=404, detail="Service not found")
        userid, webname, webtype_id, status, webtype_name = result
        tipo_servicio = next((tipo for tipo in ServicioTipo if tipo.value == webtype_name), ServicioTipo.STATIC)
        service_create = ServiceCreate(
            id_user=userid,
            tipo_servicio=[tipo_servicio],
            nombre_servicio=webname
        )
        return Service(id_service=service_id, info=service_create, status=status)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting service: {str(e)}"
        )

@router.post("/control-service/{id_service}/{action}")
async def control_service(id_service: str, action: ServiceAction):
    try:
        query = """
        SELECT userid, webname
        FROM docker_services
        WHERE id = %s
        """
        result = docker_service.db_service.fetch_one(query, (id_service,))
        if not result:
            raise HTTPException(status_code=404, detail="Service not found")
        userid, webname = result
        docker_service.control_service(userid, webname, action.value)
        return {"id_service": id_service, "status": action.value}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error controlling service: {str(e)}"
        )