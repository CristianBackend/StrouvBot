"""
Dependencias de autenticación para los endpoints. La identidad y los permisos salen SIEMPRE
del token verificado, nunca de la URL ni del body — así un owner no puede tocar otro tenant
aunque manipule la petición.
"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .models import SessionLocal, User
from .security import leer_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(cred: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    if not cred:
        raise HTTPException(401, "falta el token de sesión")
    data = leer_token(cred.credentials)
    if not data:
        raise HTTPException(401, "sesión inválida o expirada")
    s = SessionLocal()
    try:
        user = s.get(User, int(data["sub"]))
        if not user or not user.activo:
            raise HTTPException(401, "usuario no encontrado o inactivo")
        return {"id": user.id, "email": user.email, "nombre": user.nombre,
                "rol": user.rol, "tenant_id": user.tenant_id}
    finally:
        s.close()


def require_super_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["rol"] != "super_admin":
        raise HTTPException(403, "requiere permisos de administrador")
    return user


def resolve_tenant(user: dict, tid: str | None = None) -> str:
    """
    Devuelve el tenant_id sobre el que el usuario puede operar.
    - owner: siempre su propio tenant (ignora cualquier tid que intente pasar).
    - super_admin: el tid que pida (puede operar sobre cualquiera); si no pasa ninguno, error.
    """
    if user["rol"] == "super_admin":
        if not tid:
            raise HTTPException(400, "el administrador debe indicar el tenant")
        return tid
    if not user["tenant_id"]:
        raise HTTPException(403, "tu usuario no está asociado a ningún negocio")
    return user["tenant_id"]
