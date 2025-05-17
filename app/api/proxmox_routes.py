from fastapi import APIRouter, Depends, HTTPException, status, Form
from typing import Optional

from app.core.config import get_settings
from app.api.auth import get_api_key
from app.services.proxmox_service import ProxmoxService
from app.models import Sistema, VMAction, VMCreate, VM, TEMPLATE_IDS

router = APIRouter(
    dependencies=[Depends(get_api_key)]
)

settings = get_settings()

@router.get("/vm/{vm_id}", response_model=VM)
async def get_vm(vm_id: str):
    try:
        proxmox_service = ProxmoxService()
        query = """
        SELECT userid, vm_name, os, status
        FROM proxmox_vms
        WHERE vm_id = %s
        """
        result = proxmox_service.db_service.fetch_one(query, (vm_id,))
        if not result:
            raise HTTPException(status_code=404, detail="VM not found")
        userid, vm_name, os, status = result
        vm_create = VMCreate(
            userid=userid,
            sistema=Sistema(os),
            disksize=40,
            cores=2,
            memory=2048,
            ssh_pub_key=None
        )
        return VM(id_vm=vm_id, info=vm_create, status=status)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting VM: {str(e)}"
        )

@router.post("/vm", response_model=VM, status_code=status.HTTP_201_CREATED)
async def create_vm(
    userid: int = Form(...),
    vm_name: str = Form(...),
    sistema: Sistema = Form(...),
    disksize: int = Form(40),
    cores: int = Form(2),
    memory: int = Form(2048),
    ssh_pub_key: Optional[str] = Form(None)
):
    vm_data = VMCreate(
        userid=str(userid),
        vm_name=vm_name,
        sistema=sistema,
        disksize=disksize,
        cores=cores,
        memory=memory,
        ssh_pub_key=ssh_pub_key
    )
    proxmox_service = ProxmoxService()
    template_id = TEMPLATE_IDS.get(vm_data.sistema, 103)
    result = proxmox_service.clone_vm_atomic(
        userid=userid,
        node="jormundongor",
        template_id=template_id,
        vm_name=vm_name,
        os=vm_data.sistema.value,
        cores=vm_data.cores,
        memory=vm_data.memory,
        ssh_pub_key=vm_data.ssh_pub_key
    )
    if result["status"] != "success":
        raise HTTPException(status_code=500, detail=result["message"])
    return VM(id_vm=str(result["vm_id"]), info=vm_data, status="active")

@router.post("/control-vm/{id_vm}/{action}")
async def control_vm(id_vm: str, action: VMAction):
    try:
        print(f"Received id_vm: '{id_vm}' (type: {type(id_vm)})")  # Debug log
        # Remove possible whitespace and check if it's a digit
        clean_id_vm = id_vm.strip()
        if not clean_id_vm.isdigit():
            raise HTTPException(
                status_code=400,
                detail="VM ID must be a valid integer."
            )
        proxmox_service = ProxmoxService()
        result = proxmox_service.control_vm(int(clean_id_vm), action.value)
        if result["status"] != "success":
            raise HTTPException(
                status_code=500,
                detail=result.get("message", "Unknown error")
            )
        return {"id_vm": clean_id_vm, "status": result["action"]}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error controlling VM: {str(e)}"
        )