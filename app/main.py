"""
Webhook de Meta: responde 200 YA y procesa async (Meta reintenta y manda duplicados).
Idempotencia por message_id (tabla processed_messages). Debounce por cliente: las ráfagas
de 2-3 mensajes se agrupan antes de invocar al LLM.

Verificación de pago sin panel (v1): el dueño responde por WhatsApp
"PAGADO <id>" / "DESPACHADO <id>" / "CANCELADO <id>" y eso actualiza el pedido.
"""
import asyncio
import logging
import re

from fastapi import FastAPI, Request, Response
from sqlalchemy.exc import IntegrityError

from .config import DEBOUNCE_SECONDS, HISTORY_WINDOW, VERIFY_TOKEN
from .llm import ToolContext, responder
from .models import Conversation, ProcessedMessage, SessionLocal, Tenant, init_db
from .orders import cambiar_estado
from . import whatsapp as wa

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("strouv")
log.setLevel(logging.INFO)
app = FastAPI(title="Strouv — bot vendedor por WhatsApp")

# API de administración (la consume el panel Next.js)
from .admin import mount_admin  # noqa: E402
mount_admin(app)

_buffers: dict[tuple, list] = {}   # (tenant_id, cliente) -> [textos]
_tasks: dict[tuple, asyncio.Task] = {}

_OWNER_CMD = re.compile(r"^\s*(PAGADO|DESPACHADO|CANCELADO)\s+(\d+)\s*$", re.I)
_ESTADOS = {"PAGADO": "pagado", "DESPACHADO": "despachado", "CANCELADO": "cancelado"}


@app.on_event("startup")
def startup():
    init_db()


@app.get("/webhook")
async def verify(request: Request):
    p = request.query_params
    if p.get("hub.mode") == "subscribe" and p.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=p.get("hub.challenge", ""), media_type="text/plain")
    return Response(status_code=403)


@app.post("/webhook")
async def inbound(request: Request):
    body = await request.json()
    msgs = wa.parse_webhook(body)
    log.info("webhook POST recibido: %d mensaje(s) | keys=%s", len(msgs), list(body.keys()))
    for phone_id, wa_from, message_id, texto, tipo in msgs:
        log.info("  -> phone_id=%s from=%s tipo=%s", phone_id, wa_from, tipo)
        asyncio.create_task(_handle(phone_id, wa_from, message_id, texto, tipo))
    return {"ok": True}  # 200 inmediato; todo lo demás es async


async def _handle(phone_id, wa_from, message_id, texto, tipo):
    session = SessionLocal()
    try:
        # Idempotencia: ignora message_id ya vistos (Meta reintenta).
        try:
            session.add(ProcessedMessage(message_id=message_id))
            session.commit()
        except IntegrityError:
            session.rollback()
            return

        tenant = session.query(Tenant).filter(Tenant.wa_phone_id == phone_id).first()
        if not tenant:
            log.warning("phone_id sin tenant: %s", phone_id)
            return

        # Comandos del dueño: verificación de pago sin panel.
        if wa_from == tenant.owner_wa and tipo == "text":
            m = _OWNER_CMD.match(texto or "")
            if m:
                r = cambiar_estado(session, tenant.id, int(m.group(2)), _ESTADOS[m.group(1).upper()])
                msg = r.get("error") or f"✅ Pedido #{r['order_id']} → {r['estado']} ({r['nombre']}, RD${r['total']:,})"
                await wa.send_text(tenant, wa_from, msg)
                return

        # Imagen del cliente = casi siempre comprobante: pásala al flujo como evento.
        if tipo == "image":
            texto = "[el cliente envió una imagen, probablemente el comprobante de pago]"
        if not texto:
            return

        # Debounce por cliente: agrupar ráfagas antes de llamar al LLM.
        key = (tenant.id, wa_from)
        _buffers.setdefault(key, []).append(texto)
        if key in _tasks:
            _tasks[key].cancel()
        _tasks[key] = asyncio.create_task(_flush_later(key, phone_id, wa_from))
    finally:
        session.close()


async def _flush_later(key, phone_id, wa_from):
    try:
        await asyncio.sleep(DEBOUNCE_SECONDS)
    except asyncio.CancelledError:
        return
    textos, _buffers[key] = _buffers.get(key, []), []
    _tasks.pop(key, None)
    if textos:
        await _procesar(phone_id, wa_from, "\n".join(textos))


async def _procesar(phone_id, wa_from, texto):
    session = SessionLocal()
    try:
        tenant = session.query(Tenant).filter(Tenant.wa_phone_id == phone_id).first()
        conv = session.get(Conversation, (tenant.id, wa_from)) or Conversation(
            tenant_id=tenant.id, cliente_wa=wa_from, history=[])
        if conv.escalada:
            return  # un humano tiene la conversación; el bot se calla

        ctx = ToolContext(session, tenant, wa_from)
        final = await responder(ctx, list(conv.history or []), texto)

        history = list(conv.history or [])
        history += [{"role": "user", "content": texto},
                    {"role": "assistant", "content": final or "(sin texto)"}]
        conv.history = history[-HISTORY_WINDOW:]
        if ctx.escalado:
            conv.escalada = 1
        session.merge(conv)
        session.commit()

        if final:
            await wa.send_text(tenant, wa_from, final)

        # Notificaciones al dueño.
        if ctx.pedido_registrado:
            r = ctx.pedido_registrado
            await wa.send_text(tenant, tenant.owner_wa,
                f"🛒 Pedido #{r['order_id']} de {wa_from} — RD${r['total']:,} "
                f"({len(r['detalle'])} item/s). Responde PAGADO {r['order_id']} al verificar "
                f"el comprobante, o CANCELADO {r['order_id']}.")
        if ctx.escalado:
            await wa.send_text(tenant, tenant.owner_wa,
                f"⚠️ Conversación escalada: {wa_from}. El bot dejó de responderle; tómala tú.")
    except Exception:
        log.exception("procesando mensaje de %s", wa_from)
        session.rollback()
    finally:
        session.close()