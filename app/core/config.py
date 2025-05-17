# /app/core/config.py
from pydantic_settings import BaseSettings  # Cambiado desde pydantic
from functools import lru_cache
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
load_dotenv()

class Settings(BaseSettings):
    # Database settings
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_USER: str = os.getenv("DB_USER", "cloudfaster")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "qwerty-1234")
    DB_NAME: str = os.getenv("DB_NAME", "cloudfaster")

    # Proxmox settings
    PROXMOX_HOST: str = os.getenv("PROXMOX_HOST", "192.168.52.241")
    PROXMOX_USER: str = os.getenv("PROXMOX_USER", "root@pam")
    PROXMOX_PASSWORD: str = os.getenv("PROXMOX_PASSWORD", "Xugvkzm05.")
    PROXMOX_VERIFY_SSL: bool = False

    # Docker settings
    DOCKER_BASE_PATH: str = os.getenv("DOCKER_BASE_PATH", "/srv")

    # API settings
    API_TITLE: str = "Cloudfaster API"
    API_DESCRIPTION: str = "API intermediaria para gestionar VMs y servicios Docker"
    API_VERSION: str = "1.0.0"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()