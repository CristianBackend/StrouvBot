"""
Almacenamiento de imágenes con una sola interfaz: subir(bytes, filename) -> url_pública.
- Sin credenciales de Cloudinary -> guarda en disco local (uploads/) y sirve por el backend.
- Con CLOUDINARY_URL en el entorno -> sube a Cloudinary y devuelve su URL CDN.

Así el dueño sube la foto desde su teléfono hoy mismo (local), y el día que pongas
Cloudinary, cambias una variable y las fotos van a la nube sin tocar el resto del código.
"""
import os
import secrets
from pathlib import Path

CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL", "")
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "uploads"))
PUBLIC_BASE = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000")

_EXT_OK = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def _nombre_seguro(content_type: str) -> str:
    ext = _EXT_OK.get(content_type, ".jpg")
    return f"{secrets.token_hex(12)}{ext}"


def guardar_imagen(data: bytes, content_type: str, tenant_id: str) -> str:
    """Devuelve la URL pública de la imagen subida."""
    if content_type not in _EXT_OK:
        raise ValueError("formato no permitido (usa JPG, PNG o WEBP)")
    if len(data) > 5 * 1024 * 1024:
        raise ValueError("la imagen supera 5MB")

    if CLOUDINARY_URL:
        return _subir_cloudinary(data, tenant_id)

    # Local: uploads/<tenant_id>/<nombre>
    dest_dir = UPLOAD_DIR / tenant_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    nombre = _nombre_seguro(content_type)
    (dest_dir / nombre).write_bytes(data)
    return f"{PUBLIC_BASE}/uploads/{tenant_id}/{nombre}"


def _subir_cloudinary(data: bytes, tenant_id: str) -> str:
    import cloudinary
    import cloudinary.uploader
    cloudinary.config(cloudinary_url=CLOUDINARY_URL)
    res = cloudinary.uploader.upload(data, folder=f"strouv/{tenant_id}")
    return res["secure_url"]
