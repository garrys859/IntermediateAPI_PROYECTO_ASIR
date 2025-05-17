# app/services/proxmox_service.py
from proxmoxer import ProxmoxAPI
import time
import logging
from app.core.config import get_settings
from app.services.db_service import DatabaseService

logger = logging.getLogger(__name__)
settings = get_settings()

class ProxmoxService:
    def __init__(self):
        # Don't connect immediately in the constructor
        self.settings = settings
        self.proxmox = None
        self.db_service = DatabaseService(
            host=settings.DB_HOST,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME
        )
        logger.info("ProxmoxService initialized (without connection)")

    def _connect(self):
        """Establish connection with Proxmox only when needed"""
        if not self.proxmox:
            try:
                logger.info(f"Connecting to Proxmox at {self.settings.PROXMOX_HOST}")
                self.proxmox = ProxmoxAPI(
                    host=self.settings.PROXMOX_HOST,
                    user=self.settings.PROXMOX_USER,
                    password=self.settings.PROXMOX_PASSWORD,
                    verify_ssl=self.settings.PROXMOX_VERIFY_SSL,
                    timeout=30
                )
                logger.info("Proxmox connection established")
            except Exception as e:
                logger.error(f"Error connecting to Proxmox: {str(e)}")
                raise

    def clone_vm(self, userid: int, node: str, template_id: int, vm_id: int, vm_name: str, os: str, cores=2, memory=2048):
        """Clone a VM from a template and configure it"""
        self._connect()  # Connect only when needed
        try:
            # 1. Clone the template
            logger.info(f"Cloning template {template_id} to VM {vm_id}...")
            self.proxmox.nodes(node).qemu(template_id).clone.post(
                newid=vm_id,
                target=node,
                name=vm_name
            )

            # 2. Wait for VM to be ready
            self._wait_for_vm_ready(node, vm_id)

            # 3. Configure the VM
            logger.info(f"Configuring VM {vm_id}...")
            self.proxmox.nodes(node).qemu(vm_id).config.post(
                name=vm_name,
                memory=memory,
                cores=cores,
                sockets=1,
                net0="virtio,bridge=vmbr0",
                ostype="l26"
            )

            # 4. Start the VM
            logger.info(f"Starting VM {vm_id}...")
            self.proxmox.nodes(node).qemu(vm_id).status.start.post()

            # 5. Log successful creation to database
            self.db_service.log_proxmox_vm_creation(userid, vm_id, vm_name, os)

            return {
                "status": "success",
                "vm_id": vm_id,
                "vm_name": vm_name,
                "message": "VM cloned and started successfully"
            }

        except Exception as e:
            logger.error(f"Error creating VM: {e}")
            raise

    def _wait_for_vm_ready(self, node, vm_id, max_attempts=12):
        """Wait for VM to be in a ready state"""
        self._connect()  # Connect only when needed
        logger.info(f"Checking VM {vm_id} status...")
        attempts = 0

        while attempts < max_attempts:
            try:
                status = self.proxmox.nodes(node).qemu(vm_id).status.current.get()
                if status['status'] in ['stopped', 'running']:
                    logger.info(f"VM {vm_id} is ready (status: {status['status']}).")
                    return True
                else:
                    logger.info(f"VM {vm_id} is in state {status['status']}. Waiting...")
            except Exception as e:
                logger.warning(f"Error checking VM status: {e}")

            attempts += 1
            time.sleep(5)

        logger.error(f"VM {vm_id} not ready after {max_attempts} attempts")
        return False

    def control_vm(self, vm_id, action, node="sv1"):
        """Control VM state (start, stop, pause, delete)"""
        self._connect()  # Connect only when needed
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
                self.proxmox.nodes(node).qemu(vm_id).delete()
                status = "disabled"
            else:
                raise ValueError(f"Invalid action: {action}")

            # Update VM status in database
            self.db_service.update_proxmox_vm_status(vm_id, status)

            return {
                "status": "success",
                "vm_id": vm_id,
                "action": action,
                "message": f"VM {action} operation completed successfully"
            }

        except Exception as e:
            logger.error(f"Error controlling VM {vm_id} with action {action}: {e}")
            raise