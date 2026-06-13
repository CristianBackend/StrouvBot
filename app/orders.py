"""
registrar_pedido — re-cotiza internamente (el total guardado es el de cotizar, NUNCA el del
LLM) y reserva el stock ATÓMICAMENTE: UPDATE ... SET stock = stock - n WHERE stock >= n,
verificando filas afectadas. Si dos clientes compran el último frasco a la vez, solo uno gana.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from .models import Order, Product, Tenant
from .money import agregar_items, cotizar

_STOCK_COL = {"frasco": "stock_frasco", "decant": "stock_decant"}


def productos_de(session: Session, tenant_id: str) -> dict:
    rows = session.query(Product).filter(Product.tenant_id == tenant_id).all()
    return {p.id: {"nombre": p.nombre, "tipo": p.tipo, "parecido_a": p.parecido_a,
                   "notas": p.notas, "precio_frasco": p.precio_frasco,
                   "precio_decant": p.precio_decant, "stock_frasco": p.stock_frasco,
                   "stock_decant": p.stock_decant, "foto_url": p.foto_url}
            for p in rows}


def cotizar_db(session: Session, tenant: Tenant, items: list,
               metodo_envio: str = "auto", aplicar_promo: str = "auto") -> dict:
    return cotizar(productos_de(session, tenant.id), tenant.envio_config,
                   tenant.descuento_config, items, metodo_envio, aplicar_promo)


def registrar_pedido(session: Session, tenant: Tenant, cliente_wa: str, items: list,
                     nombre: str, direccion: str, telefono: str, pago: str = "",
                     metodo_envio: str = "auto") -> dict:
    cot = cotizar_db(session, tenant, items, metodo_envio)
    if "error" in cot:
        return cot  # no se registra un pedido inválido

    # Reserva atómica de stock por (producto, presentación) agregada.
    try:
        for (pid, pres), n in agregar_items(items).items():
            col = _STOCK_COL[pres]
            res = session.execute(
                text(f"UPDATE products SET {col} = {col} - :n "
                     f"WHERE id = :pid AND tenant_id = :tid AND {col} >= :n"),
                {"n": n, "pid": pid, "tid": tenant.id},
            )
            if res.rowcount != 1:
                session.rollback()
                return {"error": f"stock insuficiente al reservar: {pid} ({pres})"}

        order = Order(tenant_id=tenant.id, cliente_wa=cliente_wa, nombre=nombre,
                      direccion=direccion, telefono=telefono, items=items,
                      total=cot["total"], pago=pago)
        session.add(order)
        session.commit()
        session.expire_all()  # los UPDATE crudos invalidan la caché ORM; refrescar lecturas
    except Exception:
        session.rollback()
        raise

    return {"order_id": order.id, "estado": order.estado, "total": cot["total"],
            "detalle": cot["detalle"], "envio": cot["envio"], "descuento": cot["descuento"]}


def cambiar_estado(session: Session, tenant_id: str, order_id: int, estado: str) -> dict:
    order = (session.query(Order)
             .filter(Order.tenant_id == tenant_id, Order.id == order_id).first())
    if not order:
        return {"error": f"pedido {order_id} no existe"}
    order.estado = estado
    session.commit()
    return {"order_id": order.id, "estado": estado, "nombre": order.nombre, "total": order.total}
