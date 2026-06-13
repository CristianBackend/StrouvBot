"""Modelo de datos. Todo scoped por tenant_id (multi-tenant estricto)."""
import datetime as dt

from sqlalchemy import (JSON, Column, DateTime, ForeignKey, Integer, String, Text,
                        UniqueConstraint, create_engine)
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import DATABASE_URL

Base = declarative_base()


class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(String, primary_key=True)            # ej. "royal_oud"
    nombre = Column(String, nullable=False)
    rubro = Column(String, nullable=False)
    vertical = Column(String, nullable=False, default="perfumeria")  # perfumeria | comida (futuro)
    wa_phone_id = Column(String, unique=True, nullable=False)
    wa_token = Column(Text, nullable=False)
    owner_wa = Column(String, nullable=False)         # WhatsApp del dueño (notificación + PAGADO/DESPACHADO)
    envio_config = Column(JSON, nullable=False)       # {costo, gratis_desde, delivery_gsd}
    pago_config = Column(Text, nullable=False)        # texto descriptivo de métodos
    cuenta_mensaje = Column(Text, nullable=False)     # mensaje LITERAL con la cuenta
    descuento_config = Column(JSON, nullable=False)   # {min_frascos, monto, o_envio_gratis}
    info_extra = Column(Text, default="")
    catalogo_pdf_url = Column(Text, default="")
    activo = Column(Integer, default=1)               # el super-admin puede suspender un tenant


class User(Base):
    """
    Usuarios del panel. rol ∈ {super_admin, owner}.
    - super_admin: tú. tenant_id NULL (no pertenece a un negocio). Ve y gestiona todo.
    - owner: dueño de una tienda. tenant_id apunta a su negocio. Solo ve lo suyo.
    """
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    nombre = Column(String, default="")
    rol = Column(String, nullable=False, default="owner")
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    activo = Column(Integer, default=1)
    reset_token = Column(String, nullable=True)        # token de recuperación (hasheado)
    reset_expira = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)


class Product(Base):
    __tablename__ = "products"
    id = Column(String, primary_key=True)             # ej. "khamrah" (único por tenant)
    tenant_id = Column(String, ForeignKey("tenants.id"), primary_key=True)
    nombre = Column(String, nullable=False)
    tipo = Column(String, default="")
    parecido_a = Column(String, default="")
    notas = Column(String, default="")
    precio_frasco = Column(Integer, nullable=False)
    precio_decant = Column(Integer, nullable=False)
    stock_frasco = Column(Integer, nullable=False, default=0)
    stock_decant = Column(Integer, nullable=False, default=0)
    foto_url = Column(Text, default="")


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    cliente_wa = Column(String, nullable=False)
    nombre = Column(String, nullable=False)
    direccion = Column(Text, nullable=False)
    telefono = Column(String, nullable=False)
    items = Column(JSON, nullable=False)
    total = Column(Integer, nullable=False)           # SIEMPRE el de cotizar(), nunca el del LLM
    pago = Column(String, default="")
    estado = Column(String, nullable=False, default="pago_pendiente_verificacion")
    # estado ∈ {pago_pendiente_verificacion, pagado, despachado, cancelado}
    created_at = Column(DateTime, default=dt.datetime.utcnow)


class Conversation(Base):
    __tablename__ = "conversations"
    tenant_id = Column(String, ForeignKey("tenants.id"), primary_key=True)
    cliente_wa = Column(String, primary_key=True)
    history = Column(JSON, nullable=False, default=list)   # [{role, content: str}] — solo textos
    escalada = Column(Integer, default=0)                   # 1 = un humano tomó la conversación
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)


class ProcessedMessage(Base):
    """Idempotencia: Meta reintenta el webhook y manda duplicados."""
    __tablename__ = "processed_messages"
    message_id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)


# pool_pre_ping: verifica que la conexión esté viva antes de usarla (Neon cierra las
#   conexiones inactivas en el plan serverless; sin esto truena con "SSL connection closed").
# pool_recycle: recicla conexiones con más de 5 min para no toparse con timeouts del lado del server.
# Para SQLite (local) estos parámetros se ignoran sin problema.
_engine_kwargs = {"future": True, "pool_pre_ping": True}
if not DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["pool_recycle"] = 300

engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


def init_db():
    Base.metadata.create_all(engine)