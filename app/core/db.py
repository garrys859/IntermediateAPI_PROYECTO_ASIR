# /app/core/db.py
import mysql.connector
from mysql.connector import Error, pooling
import logging
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Tuple
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Crear un pool de conexiones para mejorar el rendimiento
try:
    connection_pool = pooling.MySQLConnectionPool(
        pool_name="cloudfaster_pool",
        pool_size=5,
        host=settings.DB_HOST,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        auth_plugin='mysql_native_password'
    )
    logger.info("Connection pool created successfully")
except Error as e:
    logger.error(f"Error creating connection pool: {e}")
    # Crear una variable None para manejar este caso
    connection_pool = None

@contextmanager
def get_connection():
    """
    Obtiene una conexión del pool y la devuelve al terminar.
    Uso como context manager:

    with get_connection() as conn:
        # usar conn
    """
    conn = None
    try:
        conn = connection_pool.get_connection()
        yield conn
    except Error as e:
        logger.error(f"Error getting connection from pool: {e}")
        # Si hay un error con el pool, intentar crear una conexión directa
        try:
            conn = mysql.connector.connect(
                host=settings.DB_HOST,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME,
                auth_plugin='mysql_native_password'
            )
            yield conn
        except Error as e2:
            logger.error(f"Error creating direct connection: {e2}")
            raise
    finally:
        if conn:
            conn.close()

def execute_query(query: str, params: Tuple = None) -> bool:
    """
    Ejecuta una consulta SQL que no devuelve resultados (INSERT, UPDATE, DELETE).

    Args:
        query: La consulta SQL a ejecutar
        params: Parámetros para la consulta (opcional)

    Returns:
        True si la consulta se ejecutó correctamente, False en caso contrario
    """
    with get_connection() as conn:
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            affected_rows = cursor.rowcount
            cursor.close()
            logger.debug(f"Query executed successfully. Affected rows: {affected_rows}")
            return True
        except Error as e:
            logger.error(f"Error executing query: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            return False

def execute_many(query: str, params_list: List[Tuple]) -> bool:
    """
    Ejecuta una consulta SQL múltiple veces con diferentes parámetros.

    Args:
        query: La consulta SQL a ejecutar
        params_list: Lista de tuplas con parámetros

    Returns:
        True si todas las consultas se ejecutaron correctamente, False en caso contrario
    """
    with get_connection() as conn:
        try:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            affected_rows = cursor.rowcount
            cursor.close()
            logger.debug(f"Query executed successfully {len(params_list)} times. Affected rows: {affected_rows}")
            return True
        except Error as e:
            logger.error(f"Error executing query multiple times: {e}")
            logger.error(f"Query: {query}")
            return False

def fetch_all(query: str, params: Tuple = None) -> List[Tuple]:
    """
    Ejecuta una consulta SQL y devuelve todos los resultados.

    Args:
        query: La consulta SQL a ejecutar
        params: Parámetros para la consulta (opcional)

    Returns:
        Lista de tuplas con los resultados
    """
    with get_connection() as conn:
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchall()
            cursor.close()
            return result
        except Error as e:
            logger.error(f"Error fetching data: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            return []

def fetch_one(query: str, params: Tuple = None) -> Optional[Tuple]:
    """
    Ejecuta una consulta SQL y devuelve el primer resultado.

    Args:
        query: La consulta SQL a ejecutar
        params: Parámetros para la consulta (opcional)

    Returns:
        Tupla con el resultado o None si no hay resultados
    """
    with get_connection() as conn:
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            return result
        except Error as e:
            logger.error(f"Error fetching data: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            return None

def fetch_dict(query: str, params: Tuple = None) -> List[Dict]:
    """
    Ejecuta una consulta SQL y devuelve los resultados como diccionarios.

    Args:
        query: La consulta SQL a ejecutar
        params: Parámetros para la consulta (opcional)

    Returns:
        Lista de diccionarios con los resultados
    """
    with get_connection() as conn:
        try:
            cursor = conn.cursor(dictionary=True)
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchall()
            cursor.close()
            return result
        except Error as e:
            logger.error(f"Error fetching data as dict: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            return []

def fetch_dict_one(query: str, params: Tuple = None) -> Optional[Dict]:
    """
    Ejecuta una consulta SQL y devuelve el primer resultado como diccionario.

    Args:
        query: La consulta SQL a ejecutar
        params: Parámetros para la consulta (opcional)

    Returns:
        Diccionario con el resultado o None si no hay resultados
    """
    with get_connection() as conn:
        try:
            cursor = conn.cursor(dictionary=True)
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            return result
        except Error as e:
            logger.error(f"Error fetching data as dict: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            return None

def get_last_insert_id() -> Optional[int]:
    """
    Obtiene el ID del último registro insertado.

    Returns:
        ID del último registro insertado o None si hay error
    """
    with get_connection() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT LAST_INSERT_ID()")
            result = cursor.fetchone()
            cursor.close()
            return result[0] if result else None
        except Error as e:
            logger.error(f"Error getting last insert ID: {e}")
            return None

def table_exists(table_name: str) -> bool:
    """
    Verifica si una tabla existe en la base de datos.

    Args:
        table_name: Nombre de la tabla a verificar

    Returns:
        True si la tabla existe, False en caso contrario
    """
    query = "SHOW TABLES LIKE %s"
    result = fetch_one(query, (table_name,))
    return result is not None