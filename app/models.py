# app/models.py
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, List

# ----
# Enumeraciones
# ----
class Sistema(str, Enum):
    WINDOWS_11 = "WINDOWS_11"
    WINDOWS_SERVER_2025 = "WINDOWS_SERVER_2025"
    WINDOWS_SERVER_2022 = "WINDOWS_SERVER_2022"
    UBUNTU24_CLIENT = "UBUNTU24_CLIENT"
    UBUNTU24_SERVER = "UBUNTU24_SERVER"
    FEDORA = "FEDORA"
    REDHAT = "REDHAT 9.5"

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
    eliminar = "eliminar"

class ServiceAction(str, Enum):
    apagar = "apagar"
    reiniciar = "reiniciar"
    encender = "encender"
    eliminar = "eliminar"

# ----
# Modelos de entrada/salida
# ----
class VMCreate(BaseModel):
    userid: str
    passwd: str = Field(..., min_length=8)
    sistema: Sistema
    disksize: int = Field(40, ge=10, le=500)
    cores: int = Field(2, ge=1, le=8)
    memory: int = Field(2048, ge=1024, le=16384)
    ssh_pub_key: Optional[str] = None

class VM(BaseModel):
    id_vm: str
    info: VMCreate
    status: str = "encendido"

class ServiceCreate(BaseModel):
    id_user: int
    tipo_servicio: List[ServicioTipo]
    nombre_servicio: str

class Service(BaseModel):
    id_service: str
    info: ServiceCreate
    status: str = "encendido"

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