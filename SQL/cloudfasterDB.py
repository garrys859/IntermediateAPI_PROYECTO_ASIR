import mysql.connector
from mysql.connector import Error

def create_connection():
    connection = None
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="cloudfaster",
            password="qwerty-1234",
            auth_plugin='mysql_native_password'
        )
    except Error as e:
        print(f"Error: {e}")
    return connection

def create_database(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
    except Error as e:
        print(f"Error: {e}")

def execute_query(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
    except Error as e:
        print(f"Error: {e}")

def main():
    # Connect to MariaDB
    connection = create_connection()
    
    # Create database
    create_database(connection, "CREATE DATABASE IF NOT EXISTS cloudfaster")
    
    # Use the cloudfaster database
    execute_query(connection, "USE cloudfaster")
    
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
    
    # Create docker_services table
    create_docker_services_table = """
    CREATE TABLE IF NOT EXISTS docker_services (
        id INT PRIMARY KEY AUTO_INCREMENT,
        userid INT,
        webname VARCHAR(255),
        webtype_id INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(50),
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE(userid, webname),
        FOREIGN KEY (webtype_id) REFERENCES webtypes(id)
    );
    """
    execute_query(connection, create_docker_services_table)
    
    # Create proxmox_vms table
    create_proxmox_vms_table = """
    CREATE TABLE IF NOT EXISTS proxmox_vms (
        id INT PRIMARY KEY AUTO_INCREMENT,
        userid INT,
        vm_id INT,
        vm_name VARCHAR(255),
        os ENUM('WINDOWS_11', 'WINDOWS_SERVER_2025', 'WINDOWS_SERVER_2022', 
                'UBUNTU24_CLIENT', 'UBUNTU24_SERVER', 'FEDORA', 'REDHAT 9.5'),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status ENUM('enabled', 'disabled')
    );
    """
    execute_query(connection, create_proxmox_vms_table)
    
    # Create api_keys table
    create_api_keys_table = """
    CREATE TABLE IF NOT EXISTS api_keys (
        id INT PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(255),
        `key` TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_used TIMESTAMP,
        is_active ENUM('enabled', 'disabled'),
        expires_at TIMESTAMP
    );
    """
    execute_query(connection, create_api_keys_table)

if __name__ == "__main__":
    main()

# Save this as create_cloudfaster_db.py
