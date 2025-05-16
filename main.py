from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, List, Dict
from uuid import uuid4

app = FastAPI(title="Virtual Machine & Service Mock API")

# ----------------------
# Enumeraciones
# ----------------------
class Sistema(str, Enum):
    windows11 = "windows11"
    windows_server_2025 = "windows server 2025"
    windows_server_2022 = "windows server 2022"
    ubuntu24_client_lts = "ubuntu 24 cliente lts"
    ubuntu24_server_lts = "ubuntu 24 server lts"
    fedora = "fedora"
    redhat = "redhat"

class ServicioTipo(str, Enum):
    STATIC = "Static"
    PHP = "PHP"
    LARAVEL = "Laravel"
    NODEJS = "Node.js"
    MYSQL = "Mysql"
    MARIADB = "Mariadb"
    PYTHON = "Python"

class VMAction(str, Enum):
    apagar = "apagar"
    pausar = "pausar"
    encender = "encender"

class ServiceAction(str, Enum):
    apagar = "apagar"
    reiniciar = "reiniciar"
    encender = "encender"

# ----------------------
# Modelos de entrada/salida
# ----------------------
class VMCreate(BaseModel):
    id_user: str
    passwd: str = Field(..., min_length=1)
    sistema: Sistema
    disksize: int = Field(..., gt=0, description="Disk size in GB")
    cores: int = Field(1, gt=0)
    memory: int = Field(..., gt=0, description="Memory in MB")
    ssh_pub_key: Optional[str] = None

class VM(BaseModel):
    id_vm: str
    info: VMCreate
    status: str = "encendido"

class ServiceCreate(BaseModel):
    id_user: str
    tipo_servicio: List[ServicioTipo]
    nombre_servicio: str

class Service(BaseModel):
    id_service: str
    info: ServiceCreate
    status: str = "encendido"

# ----------------------
# Almacenamiento en memoria
# ----------------------
vms: Dict[str, VM] = {}
services: Dict[str, Service] = {}

# ----------------------
# Endpoints
# ----------------------
@app.get("/heartbeat")
def heartbeat():
    """Comprobación sencilla de vida"""
    return {"status": "ok"}

# ----- VM -----
@app.get("/vm/{vm_id}", response_model=VM)
def get_vm(vm_id: str):
    """Información de una VM por su ID"""
    vm = vms.get(vm_id)
    if vm is None:
        raise HTTPException(status_code=404, detail="VM not found")
    return vm

@app.post("/vm", response_model=VM, status_code=201)
def create_vm(vm_data: VMCreate):
    """Crear una nueva VM"""
    vm_id = str(uuid4())
    vm = VM(id_vm=vm_id, info=vm_data)
    vms[vm_id] = vm
    return vm

@app.post("/control-vm/{id_vm}/{action}")
def control_vm(id_vm: str, action: VMAction):
    """Controlar el estado de una VM (encender, pausar o apagar).\n\nLos valores permitidos para *action* aparecen como un desplegable en la UI de Swagger."""
    vm = vms.get(id_vm)
    if vm is None:
        raise HTTPException(status_code=404, detail="VM not found")
    vm.status = action.value
    return {"id_vm": id_vm, "status": vm.status}

# ----- Service -----
@app.get("/service/{service_id}", response_model=Service)
def get_service(service_id: str):
    """Información de un servicio por su ID"""
    service = services.get(service_id)
    if service is None:
        raise HTTPException(status_code=404, detail="Service not found")
    return service

@app.post("/service", response_model=Service, status_code=201)
async def create_service(
    id_user: str = Form(...),
    tipo_servicio: List[ServicioTipo] = Form(...),
    nombre_servicio: str = Form(...),
    archivo: UploadFile = File(...)  # Archivo zip de la app
):
    """Crear un nuevo servicio a partir de un .zip subido"""
    if not archivo.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="El archivo debe ser .zip")

    info = ServiceCreate(
        id_user=id_user,
        tipo_servicio=tipo_servicio,
        nombre_servicio=nombre_servicio,
    )

    service_id = str(uuid4())
    service = Service(id_service=service_id, info=info)
    services[service_id] = service
    return service

@app.post("/control-service/{id_service}/{action}")
def control_service(id_service: str, action: ServiceAction):
    """Controlar el estado de un servicio (encender, reiniciar o apagar).\n\nLos valores permitidos para *action* aparecen como un desplegable en la UI de Swagger."""
    service = services.get(id_service)
    if service is None:
        raise HTTPException(status_code=404, detail="Service not found")
    service.status = action.value
    return {"id_service": id_service, "status": service.status}

# ----------------------
# Ejecución directa
# ----------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
