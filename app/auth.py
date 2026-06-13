"""
Endpoints de autenticación y gestión de usuarios.

Flujo de roles:
- super_admin (tú): crea tenants y crea el usuario owner de cada tenant. Ve todo.
- owner: entra a su panel, gestiona solo su negocio.

El registro público (que los dueños se registren solos) es v2: la pieza ya está lista
(crear_owner), solo falta exponerla sin auth cuando lo decidas.
"""
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from .deps import get_current_user, require_super_admin
from .mailer import enviar_reset
from .models import SessionLocal, Tenant, User
from .security import (crear_token, generar_reset_token, hash_password,
                       reset_tokens_iguales, verify_password)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: EmailStr
    password: str


@router.post("/login")
def login(body: LoginIn):
    s = SessionLocal()
    try:
        user = s.query(User).filter(User.email == body.email.lower()).first()
        if not user or not verify_password(body.password, user.password_hash):
            raise HTTPException(401, "correo o contraseña incorrectos")
        if not user.activo:
            raise HTTPException(403, "tu cuenta está desactivada")
        token = crear_token(user.id, user.rol, user.tenant_id)
        return {"token": token, "user": {"email": user.email, "nombre": user.nombre,
                                         "rol": user.rol, "tenant_id": user.tenant_id}}
    finally:
        s.close()


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user


# ── Recuperación de contraseña ───────────────────────────────────────────
class ForgotIn(BaseModel):
    email: EmailStr


@router.post("/forgot")
def forgot(body: ForgotIn):
    s = SessionLocal()
    try:
        user = s.query(User).filter(User.email == body.email.lower()).first()
        # Respuesta idéntica exista o no el correo (no filtrar qué emails están registrados).
        if user:
            raw, hashed = generar_reset_token()
            user.reset_token = hashed
            user.reset_expira = dt.datetime.utcnow() + dt.timedelta(hours=1)
            s.commit()
            enviar_reset(user.email, raw)
        return {"ok": True, "mensaje": "Si el correo existe, te enviamos un enlace."}
    finally:
        s.close()


class ResetIn(BaseModel):
    token: str
    password: str


@router.post("/reset")
def reset(body: ResetIn):
    if len(body.password) < 8:
        raise HTTPException(400, "la contraseña debe tener al menos 8 caracteres")
    s = SessionLocal()
    try:
        # Buscar por token hasheado y vigencia.
        users = s.query(User).filter(User.reset_token.isnot(None)).all()
        user = next((u for u in users if reset_tokens_iguales(body.token, u.reset_token)), None)
        if not user or not user.reset_expira or user.reset_expira < dt.datetime.utcnow():
            raise HTTPException(400, "el enlace es inválido o expiró")
        user.password_hash = hash_password(body.password)
        user.reset_token = None
        user.reset_expira = None
        s.commit()
        return {"ok": True, "mensaje": "Contraseña actualizada. Ya puedes entrar."}
    finally:
        s.close()


class CambiarPassIn(BaseModel):
    actual: str
    nueva: str


@router.post("/cambiar-password")
def cambiar_password(body: CambiarPassIn, user: dict = Depends(get_current_user)):
    if len(body.nueva) < 8:
        raise HTTPException(400, "la nueva contraseña debe tener al menos 8 caracteres")
    s = SessionLocal()
    try:
        u = s.get(User, user["id"])
        if not verify_password(body.actual, u.password_hash):
            raise HTTPException(400, "la contraseña actual no es correcta")
        u.password_hash = hash_password(body.nueva)
        s.commit()
        return {"ok": True}
    finally:
        s.close()


# ── Gestión de usuarios (solo super-admin) ───────────────────────────────
class CrearOwnerIn(BaseModel):
    email: EmailStr
    password: str
    nombre: str = ""
    tenant_id: str


@router.post("/users/owner")
def crear_owner(body: CrearOwnerIn, _: dict = Depends(require_super_admin)):
    s = SessionLocal()
    try:
        if not s.get(Tenant, body.tenant_id):
            raise HTTPException(404, "el tenant no existe; créalo primero")
        if s.query(User).filter(User.email == body.email.lower()).first():
            raise HTTPException(409, "ya existe un usuario con ese correo")
        u = User(email=body.email.lower(), password_hash=hash_password(body.password),
                 nombre=body.nombre, rol="owner", tenant_id=body.tenant_id)
        s.add(u)
        s.commit()
        return {"id": u.id, "email": u.email, "tenant_id": u.tenant_id}
    finally:
        s.close()


@router.get("/users")
def list_users(_: dict = Depends(require_super_admin)):
    s = SessionLocal()
    try:
        return [{"id": u.id, "email": u.email, "nombre": u.nombre, "rol": u.rol,
                 "tenant_id": u.tenant_id, "activo": bool(u.activo)}
                for u in s.query(User).order_by(User.created_at.desc()).all()]
    finally:
        s.close()
