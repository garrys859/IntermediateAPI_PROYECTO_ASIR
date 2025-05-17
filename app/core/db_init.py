import mysql.connector
from mysql.connector import Error
import logging
import sys
import os

# Añadir el directorio raíz al path para poder importar desde app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_connection():
    settings = get_settings()
    connection = None
    try:
        connection = mysql.connector.connect(
            host=settings.DB_HOST,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            auth_plugin='mysql_native_password'
        )
        logger.info("Conexión a MySQL establecida correctamente")
    except Error as e:
        logger.error(f"Error al conectar a MySQL: {e}")
        raise
    return connection

def create_database(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        logger.info("Base de datos creada correctamente")
    except Error as e:
        logger.error(f"Error al crear la base de datos: {e}")
        raise
    finally:
        cursor.close()

def execute_query(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
        logger.info("Consulta ejecutada correctamente")
    except Error as e:
        logger.error(f"Error al ejecutar la consulta: {e}")
        raise
    finally:
        cursor.close()

def initialize_database():
    # Connect to MariaDB
    connection = create_connection()

    # Create database
    create_database(connection, "CREATE DATABASE IF NOT EXISTS cloudfaster")

    # Use the cloudfaster database
    execute_query(connection, "USE cloudfaster")

    # Create users table
    create_users_table = """
    CREATE TABLE IF NOT EXISTS users (
        userid INT PRIMARY KEY,
        username VARCHAR(100) NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_username (username)
    );
    """
    execute_query(connection, create_users_table)

    # Create webtypes table
    create_webtypes_table = """
    CREATE TABLE IF NOT EXISTS webtypes (
        id INT PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(100) UNIQUE NOT NULL,
        description TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    );
    """
    execute_query(connection, create_webtypes_table)

    # Create docker_services table with improved indexes
    create_docker_services_table = """
    CREATE TABLE IF NOT EXISTS docker_services (
        id INT PRIMARY KEY AUTO_INCREMENT,
        userid INT NOT NULL,
        webname VARCHAR(255) NOT NULL,
        webtype_id INT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(50) DEFAULT 'active',
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE(userid, webname),
        FOREIGN KEY (userid) REFERENCES users(userid),
        FOREIGN KEY (webtype_id) REFERENCES webtypes(id),
        INDEX idx_status (status),
        INDEX idx_webtype (webtype_id),
        INDEX idx_userid (userid)
    );
    """
    execute_query(connection, create_docker_services_table)

    # Create proxmox_vms table with improved constraints
    create_proxmox_vms_table = """
    CREATE TABLE IF NOT EXISTS proxmox_vms (
        id INT PRIMARY KEY AUTO_INCREMENT,
        userid INT NOT NULL,
        vm_id INT NOT NULL,
        vm_name VARCHAR(255) NOT NULL,
        os ENUM('WINDOWS_11', 'WINDOWS_SERVER_2025', 'WINDOWS_SERVER_2022',
               'UBUNTU24_CLIENT', 'UBUNTU24_SERVER', 'FEDORA', 'REDHAT 9.5') NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status ENUM('enabled', 'disabled') DEFAULT 'enabled',
        UNIQUE(vm_id),
        FOREIGN KEY (userid) REFERENCES users(userid),
        INDEX idx_status (status),
        INDEX idx_userid (userid)
    );
    """
    execute_query(connection, create_proxmox_vms_table)

    # Create api_keys table with proper field names for compatibility
    create_api_keys_table = """
    CREATE TABLE IF NOT EXISTS api_keys (
        id INT PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(255) NOT NULL,
        api_key VARCHAR(64) NOT NULL UNIQUE,
        userid INT NOT NULL, 
        enabled BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_used TIMESTAMP NULL,
        expires_at TIMESTAMP NULL,
        FOREIGN KEY (userid) REFERENCES users(userid),
        INDEX idx_enabled (enabled),
        INDEX idx_expiry (expires_at)
    );
    """
    execute_query(connection, create_api_keys_table)

    # Insert default data
    insert_default_webtypes = """
    INSERT IGNORE INTO webtypes (id, name, description) VALUES
    (1, 'Static', 'Static website with Apache'),
    (2, 'PHP', 'PHP website with Apache'),
    (3, 'Laravel', 'Laravel PHP Framework'),
    (4, 'Node.js', 'Node.js application'),
    (5, 'MySQL', 'MySQL database'),
    (6, 'MariaDB', 'MariaDB database'),
    (7, 'Python', 'Python application with FastAPI or Flask');
    """
    execute_query(connection, insert_default_webtypes)

    # Insert default user for API key
    insert_default_user = """
    INSERT IGNORE INTO users (userid, username)
    VALUES (1, 'admin')
    """
    execute_query(connection, insert_default_user)
    
    # Create initial API key for testing
    import secrets
    api_key = secrets.token_hex(16)
    create_initial_api_key = f"""
    INSERT INTO api_keys (name, api_key, userid, enabled, expires_at)
    SELECT 'Initial API Key', '{api_key}', 1, TRUE, DATE_ADD(NOW(), INTERVAL 365 DAY)
    WHERE NOT EXISTS (SELECT 1 FROM api_keys LIMIT 1);
    """
    execute_query(connection, create_initial_api_key)

    # Show the API key if it was just created
    cursor = connection.cursor()
    cursor.execute("SELECT api_key FROM api_keys ORDER BY id LIMIT 1")
    result = cursor.fetchone()
    if result:
        logger.info(f"API Key for testing: {result[0]}")
    cursor.close()

    connection.close()
    logger.info("Inicialización de la base de datos completada")
    pass

if __name__ == "__main__":
    initialize_database()