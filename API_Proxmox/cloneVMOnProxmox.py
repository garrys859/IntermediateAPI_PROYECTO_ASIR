import time
from proxmoxer import ProxmoxAPI

# === Configuration ===

# Connexion Proxmox
PROXMOX_HOST = "192.168.52.241"
PROXMOX_USER = "root@pam"
PROXMOX_PASSWORD = "cRoTa@123"
VERIFY_SSL = False

# VM à créer
VM_ID = 9030
VM_NAME = "My-new-VM"
NODE = "sv1"
TEMPLATE_ID = 103  # ID du template à cloner

# === Fonctions ===

# 1. Cloner le template
def clone_vm(proxmox, node, template_id, vm_id):
    print(f"Clonage du template {template_id} vers la VM {vm_id}...")
    proxmox.nodes(node).qemu(template_id).clone.post(
        newid=vm_id,  # ID de la nouvelle VM
        target=node,  # Noeud cible pour la VM clonée
        name=VM_NAME   # Nom de la nouvelle VM
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
def create_vm(proxmox, node, vm_id):
    print("Création de la VM...")
    proxmox.nodes(node).qemu(vm_id).config.post(
        name=VM_NAME,
        memory=2048,  # Mémoire de la VM (en Mo)
        cores=2,      # Nombre de cœurs
        sockets=1,    # Nombre de sockets
        net0="virtio,bridge=vmbr0",  # Configuration du réseau
        ostype="l26"  # Type d'OS (Linux)
    )

# 4. Démarrer la VM
def start_vm(proxmox, node, vm_id):
    print("Démarrage de la VM...")
    proxmox.nodes(node).qemu(vm_id).status.start.post()

# === Exécution du script ===

# Connexion à l'API Proxmox
proxmox = ProxmoxAPI(PROXMOX_HOST, user=PROXMOX_USER, password=PROXMOX_PASSWORD, verify_ssl=VERIFY_SSL, timeout=30)

# 1. Cloner le template
clone_vm(proxmox, NODE, TEMPLATE_ID, VM_ID)

# 2. Attendre que la VM soit prête
wait_for_vm_ready(proxmox, NODE, VM_ID)

# 3. Créer la VM
create_vm(proxmox, NODE, VM_ID)

# 4. Démarrer la VM
start_vm(proxmox, NODE, VM_ID)

print("✅ VM clonée et démarrée avec succès.")