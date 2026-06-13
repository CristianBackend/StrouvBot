"""
Seguridad: hashing de contraseñas (bcrypt) y tokens JWT.
Nunca se guarda una contraseña en texto plano; nunca se confía en datos del cliente para
decidir identidad — la identidad sale SIEMPRE del token verificado del lado del servidor.
"""
import datetime as dt
import hashlib
import hmac
import os
import secrets

import bcrypt
import jwt

from .config import JWT_SECRET, META_APP_SECRET

JWT_ALG = "HS256"
TOKEN_HORAS = 24 * 7  # la sesión dura una semana


# ── Contraseñas ──────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except (ValueError, TypeError):
        return False


# ── JWT de sesión ────────────────────────────────────────────────────────
def crear_token(user_id: int, rol: str, tenant_id: str | None) -> str:
    payload = {
        "sub": str(user_id),
        "rol": rol,
        "tenant_id": tenant_id,
        "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=TOKEN_HORAS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def leer_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        return None


# ── Token de recuperación de contraseña ──────────────────────────────────
def generar_reset_token() -> tuple[str, str]:
    """Devuelve (token_claro_para_el_email, token_hasheado_para_la_db)."""
    raw = secrets.token_urlsafe(32)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def hash_reset_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def reset_tokens_iguales(raw: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_reset_token(raw), stored_hash or "")


# ── Firma del webhook de Meta ────────────────────────────────────────────
def verificar_firma_meta(raw_body: bytes, signature_header: str | None) -> bool:
    """Valida el header X-Hub-Signature-256: HMAC-SHA256 del body CRUDO con el App Secret.

    Sin esto, cualquiera que conozca la URL del webhook podría forjar peticiones (mensajes de
    cliente o comandos PAGADO/CANCELADO con el número del dueño). Devuelve False si no hay
    secreto configurado, falta el header, o la firma no cuadra (comparación en tiempo constante).
    """
    if not META_APP_SECRET or not signature_header or not signature_header.startswith("sha256="):
        return False
    esperado = hmac.new(META_APP_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    recibido = signature_header.split("=", 1)[1]
    return hmac.compare_digest(esperado, recibido)
