# app/api/docker_routes.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from typing import List
import logging
from uuid import uuid4
import os
import tempfile

from app.core.config import get_settings
from app.services.docker_service import DockerService
from app.api.auth import get_api_key
from app.models import Service, ServiceCreate, ServicioTipo, ServiceAction

# Create router without prefix to match the routes in the image
router = APIRouter(
    dependencies=[Depends(get_api_key)]
)

settings = get_settings()
docker_service = DockerService()
logger = logging.getLogger(__name__)

@router.post("/service", response_model=Service, status_code=status.HTTP_201_CREATED)
async def create_service(
    id_user: int = Form(...),
    tipo_servicio: ServicioTipo = Form(...),
    nombre_servicio: str = Form(...),
    archivo: UploadFile = File(None)
):
    """Create a new service from an uploaded .zip file"""
    try:
        zip_path = None

        # Save uploaded file if provided
        if archivo:
            if not archivo.filename.endswith(".zip"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File must be a .zip"
                )

            # Save the file temporarily
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            temp_file.close()

            with open(temp_file.name, "wb") as f:
                f.write(await archivo.read())

            zip_path = temp_file.name

        # Deploy service based on type
        if tipo_servicio == ServicioTipo.STATIC:
            result = docker_service.deploy_static_service(id_user, nombre_servicio, zip_path)
        else:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Service type {tipo_servicio} not yet implemented"
            )

        # Create ServiceCreate object for the response
        service_create = ServiceCreate(
            id_user=id_user,
            tipo_servicio=[tipo_servicio],
            nombre_servicio=nombre_servicio
        )

        # Generate unique ID for the service
        service_id = str(uuid4())

        return Service(id_service=service_id, info=service_create)

    except Exception as e:
        # Clean up temp file if it exists
        if zip_path and os.path.exists(zip_path):
            os.unlink(zip_path)

        logger.error(f"Error creating service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating service: {str(e)}"
        )

@router.get("/service/{service_id}", response_model=Service)
async def get_service(service_id: str):
    """Get information about a service by its ID"""
    try:
        # Query the database
        query = """
        SELECT ds.userid, ds.webname, ds.webtype_id, ds.status, wt.name as webtype_name
        FROM docker_services ds
        JOIN webtypes wt ON ds.webtype_id = wt.id
        WHERE ds.id = %s
        """
        result = docker_service.db_service.fetch_one(query, (service_id,))

        if not result:
            raise HTTPException(status_code=404, detail="Service not found")

        # Create Service object to return
        userid, webname, webtype_id, status, webtype_name = result

        # Convert webtype_name to ServicioTipo
        tipo_servicio = None
        for tipo in ServicioTipo:
            if tipo.value == webtype_name:
                tipo_servicio = tipo
                break

        if not tipo_servicio:
            tipo_servicio = ServicioTipo.STATIC

        service_create = ServiceCreate(
            id_user=userid,
            tipo_servicio=[tipo_servicio],
            nombre_servicio=webname
        )

        return Service(id_service=service_id, info=service_create, status=status)

    except Exception as e:
        logger.error(f"Error getting service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting service: {str(e)}"
        )

@router.post("/control-service/{id_service}/{action}")
async def control_service(id_service: str, action: ServiceAction):
    """Control the state of a service (start, restart, stop)"""
    try:
        # Get service information from database
        query = """
        SELECT userid, webname
        FROM docker_services
        WHERE id = %s
        """
        result = docker_service.db_service.fetch_one(query, (id_service,))

        if not result:
            raise HTTPException(status_code=404, detail="Service not found")

        userid, webname = result

        # Execute the action
        result = docker_service.control_service(userid, webname, action)
        return {"id_service": id_service, "status": action.value}

    except Exception as e:
        logger.error(f"Error controlling service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error controlling service: {str(e)}"
        )