import os
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

def save_uploaded_file(file_data, suffix=".zip") -> Optional[str]:
    if not file_data:
        return None
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_file.close()
    with open(temp_file.name, "wb") as f:
        f.write(file_data.read())
    return temp_file.name

def validate_zip_file(file_path: str) -> bool:
    try:
        with zipfile.ZipFile(file_path) as zf:
            if zf.testzip() is not None:
                return False
            base_path = Path(os.path.dirname(file_path))
            for member in zf.infolist():
                target_path = base_path / member.filename
                if not str(target_path.resolve()).startswith(str(base_path.resolve())):
                    return False
        return True
    except zipfile.BadZipFile:
        return False
    except Exception:
        return False

def generate_unique_id(prefix: str = "", length: int = 8) -> str:
    import uuid
    import base64
    random_id = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('utf-8')
    random_id = ''.join(c for c in random_id if c.isalnum())[:length]
    return f"{prefix}{random_id}"