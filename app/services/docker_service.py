# /app/services/docker_service.py
import docker
import os
import pathlib
import zipfile
import textwrap
import subprocess
import logging
from app.core.config import get_settings
from app.services.db_service import DatabaseService

logger = logging.getLogger(__name__)
settings = get_settings()

class DockerService:
    def __init__(self):
        self.client = docker.from_env()
        self.low_level = docker.APIClient()
        self.base_path = pathlib.Path(settings.DOCKER_BASE_PATH)
        self.db_service = DatabaseService(
            host=settings.DB_HOST,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME
        )
        self._ensure_network()

    def _ensure_network(self):
        """Ensure the caddy_net network exists"""
        if not any(n.name == "caddy_net" for n in self.client.networks.list()):
            logger.info("Creating caddy_net network")
            self.client.networks.create("caddy_net", driver="bridge")

    def _ensure_path(self, userid, project):
        """Ensure the project path exists"""
        # First check if user exists and get username
        user_info = self.db_service.get_user_by_userid(userid)
    
        if user_info:
            # Use username for directory structure
            username = user_info[1]  # Índice 1 corresponde a username
            target = self.base_path / "users" / str(username) / str(project)
        else:
            # Fallback to using userid directly
            target = self.base_path / "users" / str(userid) / str(project)
    
        (target / "data").mkdir(parents=True, exist_ok=True)
        (target / "filebrowser_data").mkdir(exist_ok=True)
        return target

    def _safe_extract(self, zip_path, dest_path):
        """Safely extract a zip file"""
        with zipfile.ZipFile(zip_path) as zf:
            for member in zf.infolist():
                member_path = dest_path / member.filename
                if not str(member_path.resolve()).startswith(str(dest_path.resolve())):
                    raise RuntimeError("Zip traversal detected!")
            zf.extractall(dest_path)

    def _run_once_container(self, image, cmd, volumes):
        """Run a container once and wait for it to finish"""
        self.client.containers.run(
            image=image,
            command=cmd,
            remove=True,
            volumes=volumes,
        )

    def deploy_static_service(self, userid, webname, zip_path=None, admin_pass="admin123"):
        """Deploy a static website with filebrowser"""
        try:
            # Asegurarse de que userid y webname sean strings
            userid_str = str(userid)
            webname_str = str(webname)

            target = self._ensure_path(userid_str, webname_str)

            # Extract zip if provided
            if zip_path:
                logger.info(f"Extracting {zip_path} to {target/'data'}")
                self._safe_extract(zip_path, target / "data")
                os.remove(zip_path)  # Clean up

            # Comprobar si la base de datos de filebrowser ya existe
            filebrowser_db = target / "filebrowser_data" / "filebrowser.db"

            if not filebrowser_db.exists():
                # Initialize filebrowser database
                self._run_once_container(
                    "filebrowser/filebrowser",
                    ["config", "init", "--database", "/srv/filebrowser.db"],
                    {str(target / "filebrowser_data"): {"bind": "/srv", "mode": "rw"}},
                )

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
            else:
                logger.info(f"Filebrowser database already exists at {filebrowser_db}")

            # Write docker-compose.yml
            compose_text = textwrap.dedent(f"""
            services:
              httpd:
                image: httpd:latest
                networks:
                  - caddy_net
                volumes:
                  - "./data:/usr/local/apache2/htdocs/"
                labels:
                  caddy: "{webname_str}.cloudfaster.com"
                  caddy.reverse_proxy: "{{{{upstreams 80}}}}"
                restart: always

              filebrowser:
                image: filebrowser/filebrowser:latest
                networks:
                  - caddy_net
                labels:
                  caddy: "fb-{webname_str}.cloudfaster.com"
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

            # Start services with docker compose (cambiado a docker-compose con guión)
            subprocess.run(
                ["docker-compose", "up", "-d"], cwd=target, check=True
            )

            # Log successful creation to database
            # Get webtype_id for "Static"
            webtype_id = 1  # Assuming 1 is the ID for Static webtype
            self.db_service.log_docker_service_creation(userid, webname_str, webtype_id)

            return {
                "status": "success",
                "userid": userid,
                "webname": webname_str,
                "webtype": "Static",
                "urls": {
                    "website": f"http://{webname_str}.cloudfaster.com",
                    "filebrowser": f"http://fb-{webname_str}.cloudfaster.com"
                }
            }

        except Exception as e:
            logger.error(f"Error deploying static service: {e}")
            raise

    def control_service(self, userid, webname, action):
        """Control a Docker service (start, stop, restart, delete)"""
        try:
            # Asegurarse de que userid y webname sean strings
            userid_str = str(userid)
            webname_str = str(webname)

            target = self._ensure_path(userid_str, webname_str)

            if action == "encender":
                subprocess.run(
                    ["docker-compose", "start"], cwd=target, check=True
                )
                status = "active"
            elif action == "apagar":
                subprocess.run(
                    ["docker-compose", "stop"], cwd=target, check=True
                )
                status = "stopped"
            elif action == "reiniciar":
                subprocess.run(
                    ["docker-compose", "restart"], cwd=target, check=True
                )
                status = "active"
            elif action == "eliminar":
                subprocess.run(
                    ["docker-compose", "down", "-v"], cwd=target, check=True
                )
                status = "deleted"
            else:
                raise ValueError(f"Invalid action: {action}")

            # Update service status in database
            # First get the service ID
            query = """
            SELECT id FROM docker_services
            WHERE userid = %s AND webname = %s
            """
            result = self.db_service.fetch_one(query, (userid, webname_str))

            if result:
                service_id = result[0]
                self.db_service.update_docker_service_status(service_id, status)

            return {
                "status": "success",
                "userid": userid,
                "webname": webname_str,
                "action": action,
                "message": f"Service {action} operation completed successfully"
            }

        except Exception as e:
            logger.error(f"Error controlling service: {e}")
            raise