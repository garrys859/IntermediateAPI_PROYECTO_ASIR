# /app/api/utils.py
import os
import tempfile
import zipfile
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

def save_uploaded_file(file_data, suffix=".zip") -> Optional[str]:
    """
    Guarda un archivo subido en un directorio temporal y devuelve la ruta.

    Args:
        file_data: El archivo subido
        suffix: La extensión del archivo

    Returns:
        La ruta al archivo guardado o None si hay un error
    """
    if not file_data:
        return None

    try:
        # Crear un archivo temporal
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.close()

        # Escribir el contenido del archivo
        with open(temp_file.name, "wb") as f:
            f.write(file_data.read())

        return temp_file.name
    except Exception as e:
        logger.error(f"Error al guardar el archivo: {e}")
        return None

def validate_zip_file(file_path: str) -> bool:
    """
    Valida que un archivo sea un ZIP válido y no contenga rutas peligrosas.

    Args:
        file_path: Ruta al archivo ZIP

    Returns:
        True si el archivo es válido, False en caso contrario
    """
    try:
        with zipfile.ZipFile(file_path) as zf:
            # Verificar que el archivo ZIP sea válido
            if zf.testzip() is not None:
                logger.error(f"El archivo ZIP {file_path} está corrupto")
                return False

            # Verificar que no haya rutas peligrosas
            base_path = Path(os.path.dirname(file_path))
            for member in zf.infolist():
                target_path = base_path / member.filename
                if not str(target_path.resolve()).startswith(str(base_path.resolve())):
                    logger.error(f"Intento de traversal de directorio detectado en {file_path}")
                    return False

        return True
    except zipfile.BadZipFile:
        logger.error(f"El archivo {file_path} no es un ZIP válido")
        return False
    except Exception as e:
        logger.error(f"Error al validar el archivo ZIP {file_path}: {e}")
        return False

def generate_unique_id(prefix: str = "", length: int = 8) -> str:
    """
    Genera un ID único con un prefijo opcional.

    Args:
        prefix: Prefijo para el ID
        length: Longitud del ID (sin contar el prefijo)

    Returns:
        Un ID único
    """
    import uuid
    import base64

    # Generar un UUID y codificarlo en base64
    random_id = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('utf-8')
    # Eliminar caracteres no alfanuméricos y truncar a la longitud deseada
    random_id = ''.join(c for c in random_id if c.isalnum())[:length]

    return f"{prefix}{random_id}"