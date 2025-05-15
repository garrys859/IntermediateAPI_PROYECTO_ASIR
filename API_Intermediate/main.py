from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
import uvicorn
import asyncio
from datetime import datetime
import shutil, tempfile, os, zipfile, pathlib, aiofiles
from docker_manager import docker_manager


app = FastAPI(title="Intermediate API for Proxmox and Docker")

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
    """Simulate an asynchronous processing of the Proxmox request"""
    await asyncio.sleep(2)
    print(f"Proxmox VM created for user: {proxmox_item['userid']}")

async def process_docker_request(docker_item: Dict[str, Any]):
    """Create folders and execute docker commands without blocking the main thread"""
    try:
        await asyncio.to_thread(docker_manager.handle_request, docker_item)
        print(f"[Docker] Deploy completado para {docker_item['Webname']}")
    except Exception as exc:
        print(f"[Docker] ERROR: {exc}")

@app.get("/heartbeat", response_model=HeartbeatResponse)
async def heartbeat():
    """Heartbeat endpoint to verify that the API is functioning"""
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
    zip_path: str | None = None

    if userfile:
        # guarda el contenido en un tmp seguro
        suffix = pathlib.Path(userfile.filename).suffix.lower()
        if suffix != ".zip":
            raise HTTPException(400, "Solo se aceptan archivos .zip")

        fd, zip_path = tempfile.mkstemp(suffix=".zip")
        async with aiofiles.open(fd, "wb") as out_fp:
            while chunk := await userfile.read(1024 * 1024):
                await out_fp.write(chunk)
        file_info = {"filename": userfile.filename, "stored_as": zip_path}

    
    docker_item = {
        "userid": userid,
        "Webtype": Webtype,
        "Webname": Webname,
        "zip_path": zip_path
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
        "mensaje": "Intermediate API for Proxmox and Docker",
        "proxmox_templates": [template.value for template in ProxmoxTemplate],
        "docker_webtypes": [webtype.value for webtype in DockerWebtype],
        "health_check": "/heartbeat"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
