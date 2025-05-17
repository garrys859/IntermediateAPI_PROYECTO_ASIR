import os
import pathlib
import zipfile
import subprocess
import textwrap
from app.core.config import get_settings
from app.services.db_service import DatabaseService
from app.services.docker_templates import DOCKER_TEMPLATES

settings = get_settings()

class DockerService:
    def __init__(self):
        self.base_path = pathlib.Path(settings.DOCKER_BASE_PATH)
        self.db_service = DatabaseService(
            host=settings.DB_HOST,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME
        )

    def _ensure_path(self, userid, webname):
        user_info = self.db_service.get_user_by_userid(userid)
        if user_info:
            username = user_info[1]
            target = self.base_path / "users" / str(username) / str(webname)
        else:
            target = self.base_path / "users" / str(userid) / str(webname)
        (target / "data").mkdir(parents=True, exist_ok=True)
        (target / "filebrowser_data").mkdir(exist_ok=True)
        return target

    def _safe_extract(self, zip_path, dest_path):
        with zipfile.ZipFile(zip_path) as zf:
            for member in zf.infolist():
                member_path = dest_path / member.filename
                if not str(member_path.resolve()).startswith(str(dest_path.resolve())):
                    raise RuntimeError("Zip traversal detected!")
            zf.extractall(dest_path)

    def _init_filebrowser(self, target, admin_pass="admin123"):
        filebrowser_db = target / "filebrowser_data" / "filebrowser.db"
        if not filebrowser_db.exists():
            subprocess.run([
                "docker", "run", "--rm",
                "-v", f"{str(target / 'filebrowser_data')}:/srv",
                "filebrowser/filebrowser",
                "config", "init", "--database", "/srv/filebrowser.db"
            ], check=True)
            subprocess.run([
                "docker", "run", "--rm",
                "-v", f"{str(target / 'filebrowser_data')}:/srv",
                "filebrowser/filebrowser",
                "users", "add", "admin", admin_pass,
                "--database", "/srv/filebrowser.db", "--perm.admin"
            ], check=True)

    def create_service(self, userid, webname, tipo_servicio, zip_path=None, admin_pass="admin123"):
        target = self._ensure_path(userid, webname)
        if zip_path:
            self._safe_extract(zip_path, target / "data")
            os.remove(zip_path)
        self._init_filebrowser(target, admin_pass)
        template = DOCKER_TEMPLATES.get(tipo_servicio)
        if not template:
            raise ValueError("Service type not supported")
        compose_text = textwrap.dedent(template.format(webname=webname))
        (target / "docker-compose.yml").write_text(compose_text)
        subprocess.run(["docker-compose", "up", "-d"], cwd=target, check=True)
        webtype_id = self.db_service.get_webtype_id(tipo_servicio)
        self.db_service.log_docker_service_creation(userid, webname, webtype_id)
        return {
            "status": "success",
            "userid": userid,
            "webname": webname,
            "webtype": tipo_servicio,
            "urls": {
                "website": f"http://{webname}.cloudfaster.app",
                "filebrowser": f"http://fb-{webname}.cloudfaster.app"
            }
        }

    def control_service(self, userid, webname, action):
        target = self._ensure_path(userid, webname)
        if action == "encender":
            subprocess.run(["docker-compose", "start"], cwd=target, check=True)
            status = "active"
        elif action == "apagar":
            subprocess.run(["docker-compose", "stop"], cwd=target, check=True)
            status = "stopped"
        elif action == "reiniciar":
            subprocess.run(["docker-compose", "restart"], cwd=target, check=True)
            status = "active"
        elif action == "eliminar":
            subprocess.run(["docker-compose", "down", "-v"], cwd=target, check=True)
            status = "deleted"
        else:
            raise ValueError("Invalid action")
        result = self.db_service.fetch_one(
            "SELECT id FROM docker_services WHERE userid = %s AND webname = %s",
            (userid, webname)
        )
        if result:
            service_id = result[0]
            self.db_service.update_docker_service_status(service_id, status)
        return {
            "status": "success",
            "userid": userid,
            "webname": webname,
            "action": action,
            "message": f"Service {action} operation completed successfully"
        }