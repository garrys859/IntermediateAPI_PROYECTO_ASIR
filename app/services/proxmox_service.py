from proxmoxer import ProxmoxAPI
import time
import re
from app.core.config import get_settings
from app.services.db_service import DatabaseService
import mysql.connector  # Para capturar IntegrityError

settings = get_settings()

class ProxmoxService:
    def __init__(self):
        self.settings = settings
        self.proxmox = None
        self.db_service = DatabaseService(
            host=settings.DB_HOST,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME
        )

    def _connect(self):
        if not self.proxmox:
            self.proxmox = ProxmoxAPI(
                host=self.settings.PROXMOX_HOST,
                user=self.settings.PROXMOX_USER,
                password=self.settings.PROXMOX_PASSWORD,
                verify_ssl=getattr(self.settings, "PROXMOX_VERIFY_SSL", False),
                timeout=30
            )

    def _sanitize_vm_name(self, vm_name):
        return re.sub(r'[^a-zA-Z0-9-]', '-', vm_name)[:32]

    def clone_vm_atomic(self, userid: int, node: str, template_id: int, vm_name: str, os: str, cores=2, memory=2048, ssh_pub_key=None, max_retries=5):
        self._connect()
        safe_vm_name = self._sanitize_vm_name(vm_name)
        attempt = 0
        while attempt < max_retries:
            attempt += 1
            vm_id = self.get_free_vmid(node=node)
            try:
                self.db_service.log_proxmox_vm_creation(userid, vm_id, safe_vm_name, os)
            except mysql.connector.errors.IntegrityError:
                continue
            try:
                self.proxmox.nodes(node).qemu(template_id).clone.post(
                    newid=vm_id,
                    target=node,
                    name=safe_vm_name
                )
                if ssh_pub_key and any(x in os.lower() for x in ["ubuntu", "fedora", "redhat"]):
                    self.proxmox.nodes(node).qemu(vm_id).config.post(
                        sshkeys=ssh_pub_key.replace('\n', '')
                    )
                self._wait_for_vm_ready(node, vm_id)
                self.proxmox.nodes(node).qemu(vm_id).config.post(
                    name=safe_vm_name,
                    memory=memory,
                    cores=cores,
                    sockets=1,
                    net0="virtio,bridge=vmbr0",
                    ostype="l26"
                )
                self.proxmox.nodes(node).qemu(vm_id).status.start.post()
                return {
                    "status": "success",
                    "vm_id": vm_id,
                    "vm_name": safe_vm_name,
                    "message": "VM cloned and started successfully"
                }
            except Exception as e:
                self.db_service.delete_vm_by_id(vm_id)
                if attempt >= max_retries:
                    return {
                        "status": "error",
                        "message": f"Error cloning VM after {max_retries} attempts: {str(e)}"
                    }
        return {
            "status": "error",
            "message": "Could not allocate a unique VMID after several attempts"
        }

    def _wait_for_vm_ready(self, node, vm_id, max_attempts=12):
        self._connect()
        attempts = 0
        while attempts < max_attempts:
            try:
                status = self.proxmox.nodes(node).qemu(vm_id).status.current.get()
                if status['status'] in ['stopped', 'running']:
                    return True
            except Exception:
                pass
            attempts += 1
            time.sleep(5)
        return False

    def control_vm(self, vm_id, action, node="jormundongor"):
        self._connect()
        try:
            if action == "encender":
                self.proxmox.nodes(node).qemu(vm_id).status.start.post()
                status = "enabled"
            elif action == "apagar":
                self.proxmox.nodes(node).qemu(vm_id).status.stop.post()
                status = "disabled"
            elif action == "pausar":
                self.proxmox.nodes(node).qemu(vm_id).status.suspend.post()
                status = "disabled"
            elif action == "eliminar":
                status_info = self.proxmox.nodes(node).qemu(vm_id).status.current.get()
                if status_info["status"] == "running":
                    self.proxmox.nodes(node).qemu(vm_id).status.stop.post()
                    for _ in range(12):
                        time.sleep(5)
                        status_info = self.proxmox.nodes(node).qemu(vm_id).status.current.get()
                        if status_info["status"] == "stopped":
                            break
                    else:
                        return {
                            "status": "error",
                            "message": "Failed to stop VM before deletion."
                        }
                self.proxmox.nodes(node).qemu(vm_id).delete()
                self.db_service.delete_vm_by_id(vm_id)
                status = "disabled"
            else:
                raise ValueError(f"Invalid action: {action}")
            if action != "eliminar":
                self.db_service.update_proxmox_vm_status(vm_id, status)
            return {
                "status": "success",
                "vm_id": vm_id,
                "action": action,
                "message": f"VM {action} operation completed successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error controlling VM: {str(e)}"
            }

    def get_free_vmid(self, node="jormundongor", start=1000, end=9999):
        self._connect()
        vms = self.proxmox.nodes(node).qemu.get()
        used_ids_proxmox = {int(vm['vmid']) for vm in vms if 'vmid' in vm}
        query = "SELECT vm_id FROM proxmox_vms"
        used_ids_db = {row[0] for row in self.db_service.fetch_all(query)}
        used_ids = used_ids_proxmox | used_ids_db
        for vmid in range(start, end):
            if vmid not in used_ids:
                return vmid
        raise Exception("No free VMID available")

    def delete_vm_by_id(self, vm_id):
        query = "DELETE FROM proxmox_vms WHERE vm_id = %s"
        self.db_service.execute_query(query, (vm_id,))