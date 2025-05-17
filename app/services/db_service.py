import mysql.connector
from mysql.connector import pooling
from app.core.config import get_settings

settings = get_settings()

class DatabaseService:
    def __init__(self, host, user, password, database):
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database
        }
        self.pool = pooling.MySQLConnectionPool(
            pool_name="cloudfaster_pool",
            pool_size=5,
            **self.config
        )

    def get_connection(self):
        return self.pool.get_connection()

    def execute_query(self, query, params=None):
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute(query, params or ())
            connection.commit()
            return cursor.lastrowid
        except Exception:
            if connection:
                connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def fetch_one(self, query, params=None):
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute(query, params or ())
            return cursor.fetchone()
        except Exception:
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def fetch_all(self, query, params=None):
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute(query, params or ())
            return cursor.fetchall()
        except Exception:
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def verify_api_key(self, api_key: str) -> bool:
        result = self.get_api_key(api_key)
        if result and result[2]:
            self.execute_query(
                "UPDATE api_keys SET last_used = CURRENT_TIMESTAMP WHERE api_key = %s",
                (api_key,)
            )
            return True
        return False

    def create_user(self, userid: int, username: str):
        userid_int = int(userid)
        query = """
        INSERT INTO users (userid, username)
        VALUES (%s, %s)
        """
        self.execute_query(query, (userid_int, username))
        return userid_int

    def get_user_by_userid(self, userid: int):
        query = """
        SELECT userid, username, created_at
        FROM users
        WHERE userid = %s
        """
        return self.fetch_one(query, (userid,))

    def get_user_by_username(self, username: str):
        query = """
        SELECT userid, username, created_at
        FROM users
        WHERE username = %s
        """
        return self.fetch_one(query, (username,))

    def get_user_by_userid_or_username(self, userid: int, username: str):
        query = """
        SELECT userid, username
        FROM users
        WHERE userid = %s OR username = %s
        """
        return self.fetch_one(query, (userid, username))

    def get_services_by_userid(self, userid: int):
        query = """
        SELECT ds.id, ds.webname, wt.name as webtype, ds.status,
        CONCAT('http://', ds.webname, '.cloudfaster.app') as website_url,
        CONCAT('http://fb-', ds.webname, '.cloudfaster.app') as filebrowser_url
        FROM docker_services ds
        JOIN webtypes wt ON ds.webtype_id = wt.id
        WHERE ds.userid = %s
        """
        services = self.fetch_all(query, (userid,))
        result = []
        for service in services:
            result.append({
                "id": service[0],
                "webname": service[1],
                "webtype": service[2],
                "status": service[3],
                "urls": {
                    "website": service[4],
                    "filebrowser": service[5]
                }
            })
        return result

    def get_vms_by_userid(self, userid: int):
        query = """
        SELECT id, vm_id, vm_name, os, status
        FROM proxmox_vms
        WHERE userid = %s
        """
        vms = self.fetch_all(query, (userid,))
        result = []
        for vm in vms:
            result.append({
                "id": vm[0],
                "vm_id": vm[1],
                "vm_name": vm[2],
                "os": vm[3],
                "status": vm[4]
            })
        return result

    def log_proxmox_vm_creation(self, userid: int, vm_id: int, vm_name: str, os: str):
        query = """
        INSERT INTO proxmox_vms (userid, vm_id, vm_name, os, status)
        VALUES (%s, %s, %s, %s, %s)
        """
        return self.execute_query(query, (userid, vm_id, vm_name, os, 'enabled'))

    def update_proxmox_vm_status(self, vm_id: int, status: str):
        query = """
        UPDATE proxmox_vms
        SET status = %s
        WHERE vm_id = %s
        """
        return self.execute_query(query, (status, vm_id))

    def log_docker_service_creation(self, userid, webname, webtype_id, status="active"):
        query = """
        INSERT INTO docker_services (userid, webname, webtype_id, status)
        VALUES (%s, %s, %s, %s)
        """
        self.execute_query(query, (userid, webname, webtype_id, status))

    def update_docker_service_status(self, service_id: int, status: str):
        query = """
        UPDATE docker_services
        SET status = %s
        WHERE id = %s
        """
        return self.execute_query(query, (status, service_id))

    def get_webtype_id(self, webtype_name: str):
        query = """
        SELECT id FROM webtypes WHERE name = %s
        """
        result = self.fetch_one(query, (webtype_name,))
        if result:
            return result[0]
        return None

    def get_docker_service(self, userid: int, webname: str):
        query = """
        SELECT id, webtype_id, status
        FROM docker_services
        WHERE userid = %s AND webname = %s
        """
        return self.fetch_one(query, (userid, webname))

    def get_api_key(self, api_key: str):
        query = """
        SELECT id, userid, enabled
        FROM api_keys
        WHERE api_key = %s
        """
        return self.fetch_one(query, (api_key,))
        
    def delete_vm_by_id(self, vm_id):
        query = "DELETE FROM proxmox_vms WHERE vm_id = %s"
        self.execute_query(query, (vm_id,))    

    def create_tables_if_not_exists(self):
        self.execute_query("""
        CREATE TABLE IF NOT EXISTS users (
            userid INT PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.execute_query("""
        CREATE TABLE IF NOT EXISTS webtypes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(50) NOT NULL UNIQUE,
            description VARCHAR(255)
        )
        """)
        self.execute_query("""
        CREATE TABLE IF NOT EXISTS docker_services (
            id INT AUTO_INCREMENT PRIMARY KEY,
            userid INT NOT NULL,
            webname VARCHAR(100) NOT NULL,
            webtype_id INT NOT NULL,
            status ENUM('enabled', 'disabled', 'active', 'stopped', 'deleted') NOT NULL DEFAULT 'enabled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (webtype_id) REFERENCES webtypes(id),
            UNIQUE (userid, webname)
        )
        """)
        self.execute_query("""
        CREATE TABLE IF NOT EXISTS proxmox_vms (
            id INT AUTO_INCREMENT PRIMARY KEY,
            userid INT NOT NULL,
            vm_id INT NOT NULL UNIQUE,
            vm_name VARCHAR(100) NOT NULL,
            os VARCHAR(50) NOT NULL,
            status ENUM('enabled', 'disabled') NOT NULL DEFAULT 'enabled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        """)
        self.execute_query("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INT AUTO_INCREMENT PRIMARY KEY,
            userid INT NOT NULL,
            api_key VARCHAR(64) NOT NULL UNIQUE,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP NULL,
            expires_at TIMESTAMP NULL
        )
        """)
        if not self.fetch_one("SELECT COUNT(*) FROM webtypes")[0]:
            webtypes = [
                ("Static", "Static website files"),
                ("PHP", "PHP application"),
                ("Laravel", "Laravel PHP framework"),
                ("Node.js", "Node.js application"),
                ("Mysql", "MySQL database"),
                ("Mariadb", "MariaDB database"),
                ("Python", "Python application")
            ]
            for webtype in webtypes:
                self.execute_query(
                    "INSERT INTO webtypes (name, description) VALUES (%s, %s)",
                    webtype
                )