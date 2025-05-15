from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
import uvicorn
import asyncio
from datetime import datetime
import time
from proxmoxer import ProxmoxAPI

app = FastAPI(title="API Intermediaria para Proxmox y Docker")

# Proxmox Credentials
PROXMOX_HOST = "192.168.52.241"
PROXMOX_USER = "root@pam"
PROXMOX_PASSWORD = "cRoTa@123"
VERIFY_SSL = False

# Connexion to Proxmox API
proxmox = ProxmoxAPI(PROXMOX_HOST, user=PROXMOX_USER, password=PROXMOX_PASSWORD, verify_ssl=VERIFY_SSL, timeout=30)

#======Functions========
# 1. Cloner le template
def clone_vm(proxmox, node, template_id, vm_id, vm_name):
    print(f"Clonage du template {template_id} vers la VM {vm_id}...")
    proxmox.nodes(node).qemu(template_id).clone.post(
        newid=vm_id,  # ID de la nouvelle VM
        target=node,  # Noeud cible pour la VM clonée
        name=vm_name   # Nom de la nouvelle VM
    )

# 2. Attendre que la VM soit prête
def wait_for_vm_ready(proxmox, node, vm_id):
    print(f"Vérification de l'état de la VM {vm_id}...")
    while True:
        # Vérifie l'état de la VM
        status = proxmox.nodes(node).qemu(vm_id).status.current.get()
        if status['status'] == 'stopped':  # Si la VM est arrêtée, on peut continuer
            print(f"La VM {vm_id} est prête.")
            break
        elif status['status'] == 'running':  # Si la VM est en cours d'exécution, elle est prête
            print(f"La VM {vm_id} est en cours d'exécution.")
            break
        else:
            print(f"La VM {vm_id} est dans un état inconnu ({status['status']}). Réessayer...")
        
        time.sleep(5)  # Attente de 5 secondes avant la prochaine vérification

# 3. Création de la VM via API
def create_vm(proxmox, node, vm_id, vm_name, disksize, cores, memory):
    print("Création de la VM...")
    proxmox.nodes(node).qemu(vm_id).config.post(
        name=vm_name,
        memory=memory,  # Memory of VM (in MB)
        cores=cores,      # Number of cores
        sockets=1,    # Numbers of sockets
        net0="virtio,bridge=vmbr0",  # Network configuration
        # disksize=disksize,  # Disk size (in GB)
        ostype="l26"  # OS type (Linux)
    )

# 4. Démarrer la VM
def start_vm(proxmox, node, vm_id):
    print("Démarrage de la VM...")
    proxmox.nodes(node).qemu(vm_id).status.start.post()
    
    
def create_vm_and_start(proxmox, node, template_id, vm_id, vm_name, disksize, cores, memory):
    clone_vm(proxmox, node, template_id, vm_id, vm_name)
    wait_for_vm_ready(proxmox, node, vm_id)
    create_vm(proxmox, node, vm_id, disksize, cores, memory)
    start_vm(proxmox, node, vm_id)
    print(f"VM {vm_id} créée et démarrée avec succès.")
    
#====End Functions====

class ProxmoxTemplate(str, Enum):
    WINDOWS_11 = "Windows 11"
    WINDOWS_SERVER_2025 = "Windows Server 2025"
    WINDOWS_SERVER_2022 = "Windows Server 2022"
    UBUNTU24C = "Ubuntu 24 Client LTS"
    UBUNTU24S = "Ubuntu 24 Server LTS"
    FEDORA = "Fedora"
    REDHAT = "RedHat"

class DockerWebtype(str, Enum):
    ESTATICO = "Estatico"
    PHP = "PHP"
    LARAVEL = "Laravel"
    REACT_VITE = "React/Vite"
    NODE = "Node"
    NEXT = "Next"
    VITE = "Vite"
    WORDPRESS = "WordPress"
    MYSQL = "MySQL"
    MARIADB = "MariaDB"
    POSTGRES = "Postgress"
    REDIS = "Redis"
    MONGODB = "MongoDB"
    VSCODE_SERVER = "VSCode Server"

class Proxmox(BaseModel):
    userid: str
    upassword: str
    os: ProxmoxTemplate
    disksize: int
    cores: int = Field(default=1)
    memory: int
    sshpb: Optional[str] = None

class Docker(BaseModel):
    userid: str
    Webtype: DockerWebtype
    Webname: str

class HeartbeatResponse(BaseModel):
    status: str
    timestamp: str
    uptime: float
    version: str

proxmox_items = []
docker_items = []
start_time = datetime.now()
api_version = "1.2.0"
async def process_proxmox_request(proxmox_item: Dict[str, Any]):
    """Simular un procesamiento asincrono de la solicitud de Proxmox"""
    await asyncio.sleep(2)
    print(f"Proxmox VM creada para usuario: {proxmox_item['userid']}")

async def process_docker_request(docker_item: Dict[str, Any]):
    """Simular un procesamiento asincrono de la solicitud de Docker"""
    await asyncio.sleep(1)
    print(f"Contenedor Docker creado: {docker_item['Webname']}")

@app.get("/heartbeat", response_model=HeartbeatResponse)
async def heartbeat():
    """Endpoint de heartbeat para verificar que la API esta funcionando"""
    uptime = (datetime.now() - start_time).total_seconds()
    return {
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "uptime": uptime,
        "version": api_version
    }

@app.post("/proxmox/")
async def create_proxmox(
    background_tasks: BackgroundTasks,
    userid: str = Form(...),
    upassword: str = Form(...),
    os: ProxmoxTemplate = Form(...),
    disksize: int = Form(...),
    cores: int = Form(1),
    memory: int = Form(...),
    sshpb: Optional[str] = Form(None)
):
    proxmox_item = Proxmox(
        userid=userid,
        upassword=upassword,
        os=os,
        disksize=disksize,
        cores=cores,
        memory=memory,
        sshpb=sshpb
    )
    proxmox_items.append(proxmox_item)
    background_tasks.add_task(process_proxmox_request, proxmox_item.dict())
    
    create_vm_and_start(proxmox, "sv1", os, "random number???", userid, disksize, cores, memory)
    
    return {
        "status": "processing",
        "message": "Proxmox VM creation started",
        "vm_details": proxmox_item
    }

@app.get("/proxmox/", response_model=List[Proxmox])
async def read_proxmox():
    return proxmox_items

@app.get("/proxmox/{item_id}", response_model=Proxmox)
async def read_proxmox_item(item_id: int):
    if item_id < 0 or item_id >= len(proxmox_items):
        raise HTTPException(status_code=404, detail="Item not found")
    return proxmox_items[item_id]

@app.post("/docker/")
async def create_docker(
    background_tasks: BackgroundTasks,
    userid: str = Form(...),
    Webtype: DockerWebtype = Form(...),
    Webname: str = Form(...),
    userfile: Optional[UploadFile] = File(None)
):
    file_info = None
    if userfile:
        file_info = {
            "filename": userfile.filename,
            "content_type": userfile.content_type,
        }
    
    docker_item = {
        "userid": userid,
        "Webtype": Webtype,
        "Webname": Webname,
        "userfile": file_info
    }
    
    docker_items.append(docker_item)
    background_tasks.add_task(process_docker_request, docker_item)
    
    return {
        "status": "processing",
        "message": "Docker container creation started",
        "container_details": docker_item
    }

@app.get("/docker/")
async def read_docker():
    return docker_items

@app.get("/docker/{item_id}")
async def read_docker_item(item_id: int):
    if item_id < 0 or item_id >= len(docker_items):
        raise HTTPException(status_code=404, detail="Item not found")
    return docker_items[item_id]

@app.get("/")
async def read_root():
    return {
        "mensaje": "API Intermediaria para Proxmox y Docker",
        "proxmox_templates": [template.value for template in ProxmoxTemplate],
        "docker_webtypes": [webtype.value for webtype in DockerWebtype],
        "health_check": "/heartbeat"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)