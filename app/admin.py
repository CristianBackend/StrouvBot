"""
API de administración (REST) que consume el panel. AHORA protegida por auth:
- Todo endpoint exige token válido (get_current_user).
- El tenant sobre el que se opera sale del token (resolve_tenant), no de la URL:
  un owner solo toca SU negocio; el super_admin puede indicar cuál con ?tenant=.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func

from .config import PANEL_URL
from .deps import get_current_user, require_super_admin, resolve_tenant
from .models import Conversation, Order, Product, SessionLocal, Tenant, User
from .security import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Schemas ──────────────────────────────────────────────────────────────
class TenantIn(BaseModel):
    id: str | None = None
    nombre: str
    rubro: str
    vertical: str = "perfumeria"
    wa_phone_id: str = ""
    wa_token: str = ""
    owner_wa: str = ""
    envio_config: dict
    pago_config: str
    cuenta_mensaje: str
    descuento_config: dict
    info_extra: str = ""
    catalogo_pdf_url: str = ""


class ProductIn(BaseModel):
    id: str
    nombre: str
    tipo: str = ""
    parecido_a: str = ""
    notas: str = ""
    precio_frasco: int
    precio_decant: int
    stock_frasco: int = 0
    stock_decant: int = 0
    foto_url: str = ""


def _tenant_dict(t: Tenant) -> dict:
    return {c.name: getattr(t, c.name) for c in t.__table__.columns}


def _product_dict(p: Product) -> dict:
    return {c.name: getattr(p, c.name) for c in p.__table__.columns}


# ── Tenants ──────────────────────────────────────────────────────────────
@router.get("/tenants")
def list_tenants(user: dict = Depends(get_current_user)):
    """super_admin ve todos; owner ve solo el suyo."""
    s = SessionLocal()
    try:
        q = s.query(Tenant)
        if user["rol"] != "super_admin":
            q = q.filter(Tenant.id == user["tenant_id"])
        out = []
        for t in q.all():
            prods = s.query(Product).filter(Product.tenant_id == t.id).count()
            pedidos = s.query(Order).filter(Order.tenant_id == t.id).count()
            out.append({**_tenant_dict(t), "n_productos": prods, "n_pedidos": pedidos})
        return out
    finally:
        s.close()


@router.get("/tenant")
def get_my_tenant(user: dict = Depends(get_current_user),
                  tenant: str | None = Query(None)):
    tid = resolve_tenant(user, tenant)
    s = SessionLocal()
    try:
        t = s.get(Tenant, tid)
        if not t:
            raise HTTPException(404, "tenant no existe")
        return _tenant_dict(t)
    finally:
        s.close()


@router.post("/tenants")
def create_tenant(body: TenantIn, _: dict = Depends(require_super_admin)):
    """Crear/editar un tenant es solo del super-admin."""
    s = SessionLocal()
    try:
        tid = body.id or body.nombre.lower().replace(" ", "_")
        t = s.get(Tenant, tid)
        data = body.model_dump(exclude={"id"})
        if t:
            for k, v in data.items():
                setattr(t, k, v)
        else:
            t = Tenant(id=tid, **data)
            s.add(t)
        s.commit()
        return _tenant_dict(t)
    finally:
        s.close()


class TenantConfigIn(BaseModel):
    """Lo que un owner SÍ puede editar de su propio negocio (no toca id ni vertical)."""
    nombre: str
    rubro: str
    owner_wa: str = ""
    wa_phone_id: str = ""
    wa_token: str = ""
    envio_config: dict
    pago_config: str
    cuenta_mensaje: str
    descuento_config: dict
    info_extra: str = ""
    catalogo_pdf_url: str = ""


@router.put("/tenant")
def update_my_tenant(body: TenantConfigIn, user: dict = Depends(get_current_user),
                     tenant: str | None = Query(None)):
    tid = resolve_tenant(user, tenant)
    s = SessionLocal()
    try:
        t = s.get(Tenant, tid)
        if not t:
            raise HTTPException(404, "tenant no existe")
        for k, v in body.model_dump().items():
            setattr(t, k, v)
        s.commit()
        return _tenant_dict(t)
    finally:
        s.close()


# ── Products ─────────────────────────────────────────────────────────────
@router.get("/products")
def list_products(user: dict = Depends(get_current_user), tenant: str | None = Query(None)):
    tid = resolve_tenant(user, tenant)
    s = SessionLocal()
    try:
        return [_product_dict(p) for p in
                s.query(Product).filter(Product.tenant_id == tid).all()]
    finally:
        s.close()


@router.post("/products")
def upsert_product(body: ProductIn, user: dict = Depends(get_current_user),
                   tenant: str | None = Query(None)):
    tid = resolve_tenant(user, tenant)
    s = SessionLocal()
    try:
        p = s.get(Product, (body.id, tid))
        data = body.model_dump()
        if p:
            for k, v in data.items():
                setattr(p, k, v)
        else:
            p = Product(tenant_id=tid, **data)
            s.add(p)
        s.commit()
        return _product_dict(p)
    finally:
        s.close()


@router.delete("/products/{pid}")
def delete_product(pid: str, user: dict = Depends(get_current_user),
                   tenant: str | None = Query(None)):
    tid = resolve_tenant(user, tenant)
    s = SessionLocal()
    try:
        p = s.get(Product, (pid, tid))
        if not p:
            raise HTTPException(404, "producto no existe")
        s.delete(p)
        s.commit()
        return {"ok": True}
    finally:
        s.close()


# ── Orders ───────────────────────────────────────────────────────────────
@router.get("/orders")
def list_orders(user: dict = Depends(get_current_user), tenant: str | None = Query(None)):
    tid = resolve_tenant(user, tenant)
    s = SessionLocal()
    try:
        rows = (s.query(Order).filter(Order.tenant_id == tid)
                .order_by(Order.created_at.desc()).limit(200).all())
        return [{"id": o.id, "cliente_wa": o.cliente_wa, "nombre": o.nombre,
                 "direccion": o.direccion, "telefono": o.telefono, "items": o.items,
                 "total": o.total, "pago": o.pago, "estado": o.estado,
                 "created_at": o.created_at.isoformat() if o.created_at else None}
                for o in rows]
    finally:
        s.close()


class EstadoIn(BaseModel):
    estado: str


@router.patch("/orders/{oid}")
def set_order_estado(oid: int, body: EstadoIn, user: dict = Depends(get_current_user),
                     tenant: str | None = Query(None)):
    tid = resolve_tenant(user, tenant)
    valid = {"pago_pendiente_verificacion", "pagado", "despachado", "cancelado"}
    if body.estado not in valid:
        raise HTTPException(400, f"estado inválido: {body.estado}")
    s = SessionLocal()
    try:
        o = s.query(Order).filter(Order.tenant_id == tid, Order.id == oid).first()
        if not o:
            raise HTTPException(404, "pedido no existe")
        o.estado = body.estado
        s.commit()
        return {"id": o.id, "estado": o.estado}
    finally:
        s.close()


# ── Métricas ─────────────────────────────────────────────────────────────
@router.get("/metrics")
def metrics(user: dict = Depends(get_current_user), tenant: str | None = Query(None)):
    tid = resolve_tenant(user, tenant)
    s = SessionLocal()
    try:
        by_estado = dict(
            s.query(Order.estado, func.count(Order.id))
            .filter(Order.tenant_id == tid).group_by(Order.estado).all())
        total_pedidos = sum(by_estado.values())
        ingresos = (s.query(func.coalesce(func.sum(Order.total), 0))
                    .filter(Order.tenant_id == tid,
                            Order.estado.in_(["pagado", "despachado"])).scalar())
        convs = s.query(Conversation).filter(Conversation.tenant_id == tid).count()
        return {
            "conversaciones": convs,
            "pedidos": total_pedidos,
            "por_estado": by_estado,
            "ingresos_confirmados": int(ingresos or 0),
            "conversion": round(total_pedidos / convs, 3) if convs else 0,
        }
    finally:
        s.close()


# ── Métricas globales (solo super-admin) ─────────────────────────────────
@router.get("/overview")
def overview(_: dict = Depends(require_super_admin)):
    s = SessionLocal()
    try:
        tenants = s.query(Tenant).count()
        pedidos = s.query(Order).count()
        ingresos = (s.query(func.coalesce(func.sum(Order.total), 0))
                    .filter(Order.estado.in_(["pagado", "despachado"])).scalar())
        return {"tenants": tenants, "pedidos": pedidos,
                "ingresos_confirmados": int(ingresos or 0)}
    finally:
        s.close()



# ── Subida de imágenes ───────────────────────────────────────────────────
from fastapi import UploadFile, File  # noqa: E402
from .storage import guardar_imagen  # noqa: E402


@router.post("/upload")
async def upload_imagen(file: UploadFile = File(...),
                        user: dict = Depends(get_current_user),
                        tenant: str | None = Query(None)):
    tid = resolve_tenant(user, tenant)
    data = await file.read()
    try:
        url = guardar_imagen(data, file.content_type or "", tid)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"url": url}


def mount_admin(app):
    # Servir las imágenes subidas localmente (en producción con Cloudinary esto no se usa)
    import os
    from fastapi.staticfiles import StaticFiles
    os.makedirs("uploads", exist_ok=True)
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
    app.add_middleware(
        CORSMiddleware, allow_origins=[PANEL_URL, "http://localhost:3000"],
        allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    from .auth import router as auth_router
    app.include_router(auth_router)
    app.include_router(router)
