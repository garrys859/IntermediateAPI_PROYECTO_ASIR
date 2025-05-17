import mysql.connector
from mysql.connector import Error
import sys
import os
from app.core.config import get_settings

def create_connection():
    settings = get_settings()
    return mysql.connector.connect(
        host=settings.DB_HOST,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        auth_plugin='mysql_native_password'
    )

def create_database(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
    finally:
        cursor.close()

def execute_query(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
    finally:
        cursor.close()

def initialize_database():
    connection = create_connection()
    create_database(connection, "CREATE DATABASE IF NOT EXISTS cloudfaster")
    execute_query(connection, "USE cloudfaster")

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

    insert_default_user = """
    INSERT IGNORE INTO users (userid, username)
    VALUES (1, 'admin')
    """
    execute_query(connection, insert_default_user)

    import secrets
    api_key = secrets.token_hex(16)
    create_initial_api_key = f"""
    INSERT INTO api_keys (name, api_key, userid, enabled, expires_at)
    SELECT 'Initial API Key', '{api_key}', 1, TRUE, DATE_ADD(NOW(), INTERVAL 365 DAY)
    WHERE NOT EXISTS (SELECT 1 FROM api_keys LIMIT 1);
    """
    execute_query(connection, create_initial_api_key)

    cursor = connection.cursor()
    cursor.execute("SELECT api_key FROM api_keys ORDER BY id LIMIT 1")
    result = cursor.fetchone()
    if result:
        print(f"API Key for testing: {result[0]}")
    cursor.close()
    connection.close()

if __name__ == "__main__":
    initialize_database()