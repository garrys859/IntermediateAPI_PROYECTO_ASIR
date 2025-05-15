# docker_manager.py
import os
import subprocess
import pathlib
from typing import Dict
import docker
import zipfile, os, pathlib, shutil, textwrap

# Cambiar este path a la ruta donde se guardarán los servicios de los usuarios
# Change this path to the path where the user's services will be saved
BASE_PATH = pathlib.Path("/home/fastapi/prueba/srv/users")  # cámbialo si necesitas otra raíz
# Dominio
domain = 'mercuriosftp.sytes.net'

class DockerManager:
    """
    Orquesta la creación de contenedores sueltos y stacks docker-compose
    a partir de la información recibida por la API. 

    Orchestrates the creation of standalone containers and docker-compose stacks
    based on information received from the API.
    """

    def __init__(self):
        # Cliente docker api de alto nivel
        # high level docker api client
        self.client = docker.from_env()
        self.low_level = docker.APIClient()
        self._ensure_network()

    # ---------- utilidades internas ----------
    # ---------- internal utilities ----------

    # Creamos las carpetas necesarias
    # Data para los archivos del usuario de la página
    # filebrowser_data para el archivo de la base de datos de filebrowser
    def _ensure_path(self, user: str, project: str) -> pathlib.Path:
        target = BASE_PATH / user / project
        (target / "data").mkdir(parents=True, exist_ok=True)
        (target / "filebrowser_data").mkdir(exist_ok=True)
        return target

    def _run_once_container(
        self, image: str, cmd: str | list[str], volumes: Dict[str, dict]
    ):
        """
        Ejecuta un contenedor efímero (`--rm`) y espera a que termine
        (equivalente a tus dos comandos de `docker run --rm …`).

        Run a temporary container (`--rm`) and wait for it to finish
        (equivalent to your two `docker run --rm …` commands).
        """
        self.client.containers.run(
            image=image,
            command=cmd,
            remove=True,
            volumes=volumes,
        )

    # Creamos la red si no existe
    # Create the network if it doesn't exist
    def _ensure_network(self):
        if not any(n.name == "caddy_net" for n in self.client.networks.list()):
            self.client.networks.create("caddy_net", driver="bridge")

    # Descomprime el zip de manera segura
    # Safely extract the zip
    def _safe_extract(self, zf: zipfile.ZipFile, dest: pathlib.Path):
        for member in zf.infolist():
            member_path = dest / member.filename
            if not str(member_path.resolve()).startswith(str(dest.resolve())):
                raise RuntimeError("Zip traversal detected!")
        zf.extractall(dest)

    # ---------- casos públicos ----------
    # ---------- public cases ----------

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Stack estático con filebrowser
    # Static stack with filebrowser
    def deploy_static_with_filebrowser(
        # TODO: Generar contraseña aleatoria o usar la que el usuario elija
        # TODO: Generate a random password or use the one the user chooses
        self, user: str, project: str, zip_path: str | None, admin_pass: str = "admin123"
    ):
        """
        Crea el stack en la carpeta del usuario.
        Creates the stack in the user's folder.
        """
        target = self._ensure_path(user, project)

        # 0) Descomprimir el zip
        if zip_path:
            print(f"Extracting {zip_path} → {target/'data'}")
            with zipfile.ZipFile(zip_path) as zf:
                self._safe_extract(zf, target / "data")
            os.remove(zip_path)  # limpia tmp | Clear tmp

        # 1) Inicializar DB
        # Initialize DB
        self._run_once_container(
            "filebrowser/filebrowser",
            ["config", "init", "--database", "/srv/filebrowser.db"],
            {str(target / "filebrowser_data"): {"bind": "/srv", "mode": "rw"}},
        )

        # 2) Crear usuario admin
        # Create admin user
        self._run_once_container(
            "filebrowser/filebrowser",
            [
                "users",
                "add",
                "admin",
                admin_pass,
                "--database",
                "/srv/filebrowser.db",
                "--perm.admin",
            ],
            {str(target / "filebrowser_data"): {"bind": "/srv", "mode": "rw"}},
        )

        # 3) Escribir docker-compose.yml
        # Puse el dominio mio personal, cambiar al dominio de clase cloudfaster.com
        # Write docker-compose.yml
        # I used my personal domain, change to cloudfaster.com
        compose_text = textwrap.dedent(f"""
        services:
          httpd:
            image: httpd:latest
            networks:
              - caddy_net
            volumes:
              - "./data:/usr/local/apache2/htdocs/"
            labels:
              caddy: "{project}.{domain}"
              caddy.reverse_proxy: "{{{{upstreams 80}}}}"
            restart: always

          filebrowser:
            image: filebrowser/filebrowser:latest
            networks:
              - caddy_net
            labels:
              caddy: "fb-{project}.{domain}"
              caddy.reverse_proxy: "{{{{upstreams 80}}}}"
            volumes:
              - "./filebrowser_data/filebrowser.db:/database.db"
              - "./data:/srv"
            command: --database /database.db
            restart: always

        networks:
          caddy_net:
            external: true
        """)
        (target / "docker-compose.yml").write_text(compose_text)

        # 4) Levantar servicios con docker compose v2
        subprocess.run(
            ["docker", "compose", "up", "-d"], cwd=target, check=True
        )
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Aquí empieza el siguiente stack
    # Here starts the next stack

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # ---------- punto de entrada principal ----------
    # ---------- main entry point ----------
    def handle_request(self, payload: Dict):
        """
        Decide qué hacer según el `Webtype` recibido desde FastAPI.
        Lanza la rutina adecuada.

        Decides what to do according to the `Webtype` received from FastAPI.
        Launches the appropriate routine.
        """
        wtype = payload["Webtype"]
        user = payload["userid"]
        pname = payload["Webname"]

        if wtype == "Estatico":
            self.deploy_static_with_filebrowser(user, pname, payload.get("zip_path"))
        #elif wtype == "PHP":
            #self.deploy_php_with_caddy(user, pname, payload.get("zip_path"))
        else:
            # Esqueleto para futuros tipos
            # Skeleton for future types
            raise NotImplementedError(f"Webtype {wtype} aún no soportado")

# Helper singleton para no re-crear cliente cada vez
# Helper singleton to avoid re-creating the client each time
docker_manager = DockerManager()
