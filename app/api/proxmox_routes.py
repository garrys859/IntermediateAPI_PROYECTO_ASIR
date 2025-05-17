# app/api/proxmox_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import logging

from app.core.config import get_settings
from app.api.auth import get_api_key
from app.services.proxmox_service import ProxmoxService
from app.models import Sistema, VMAction, VMCreate, VM, TEMPLATE_IDS

# Create router without prefix to match the routes in the image
router = APIRouter(
    dependencies=[Depends(get_api_key)]
)

settings = get_settings()
logger = logging.getLogger(__name__)

# Template IDs for different OS types
TEMPLATE_IDS = {
    Sistema.WINDOWS_11: 101,
    Sistema.WINDOWS_SERVER_2025: 102,
    Sistema.WINDOWS_SERVER_2022: 103,
    Sistema.UBUNTU24_CLIENT: 104,
    Sistema.UBUNTU24_SERVER: 105,
    Sistema.FEDORA: 106,
    Sistema.REDHAT: 107
}

@router.get("/vm/{vm_id}", response_model=VM)
async def get_vm(vm_id: str):
    """Get information about a VM by its ID"""
    try:
        proxmox_service = ProxmoxService()

        # Query the database
        query = """
        SELECT userid, vm_name, os, status
        FROM proxmox_vms
        WHERE vm_id = %s
        """
        result = proxmox_service.db_service.fetch_one(query, (vm_id,))

        if not result:
            raise HTTPException(status_code=404, detail="VM not found")

        # Create VM object to return
        userid, vm_name, os, status = result
        vm_create = VMCreate(
            id_user=userid,
            passwd="*****",  # Don't return the real password
            sistema=os,
            disksize=40,  # Default values
            cores=2,
            memory=2048,
            ssh_pub_key=None
        )

        return VM(id_vm=vm_id, info=vm_create, status=status)

    except Exception as e:
        logger.error(f"Error getting VM: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting VM: {str(e)}"
        )

@router.post("/vm", response_model=VM, status_code=status.HTTP_201_CREATED)
async def create_vm(vm_data: VMCreate):
    """Create a new VM"""
    try:
        proxmox_service = ProxmoxService()

        # Generate a unique VM ID (in a real system, this would be more sophisticated)
        vm_id = 9000 + vm_data.id_user  # Simple example

        # Generate VM name
        vm_name = f"{vm_data.sistema.value}-{vm_data.id_user}"

        # Get template ID for the selected OS
        template_id = TEMPLATE_IDS.get(vm_data.sistema, 103)  # Default to Windows Server 2022

        # Clone and configure the VM
        result = proxmox_service.clone_vm(
            userid=vm_data.id_user,
            node="sv1",  # Adjust according to your environment
            template_id=template_id,
            vm_id=vm_id,
            vm_name=vm_name,
            os=vm_data.sistema.value,
            cores=vm_data.cores,
            memory=vm_data.memory
        )

        # Create VM object to return
        return VM(id_vm=str(vm_id), info=vm_data, status="encendido")

    except Exception as e:
        logger.error(f"Error creating VM: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating VM: {str(e)}"
        )

@router.post("/control-vm/{id_vm}/{action}")
async def control_vm(id_vm: str, action: VMAction):
    """Control the state of a VM (start, pause, stop)"""
    try:
        proxmox_service = ProxmoxService()

        result = proxmox_service.control_vm(int(id_vm), action)
        return {"id_vm": id_vm, "status": result["action"]}

    except Exception as e:
        logger.error(f"Error controlling VM: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error controlling VM: {str(e)}"
        )