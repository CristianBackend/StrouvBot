"""
Cerebro LLM (Fable). El loop de tools trabaja sobre una copia LOCAL del historial;
al historial persistido solo entran textos (serializable y barato). Una excepción en una
tool vuelve al modelo como tool_result {"error": ...} — NUNCA tumba la respuesta:
en WhatsApp, silencio = venta muerta.
"""
import asyncio
import json
import logging
from pathlib import Path

import anthropic

from .config import HISTORY_WINDOW, MODEL_BRAIN
from .models import Tenant
from .orders import cotizar_db, productos_de, registrar_pedido
from . import whatsapp as wa

log = logging.getLogger("strouv.llm")
claude = anthropic.Anthropic()  # ANTHROPIC_API_KEY del entorno

PROMPT_TEMPLATE = (Path(__file__).parent / "prompt_template.md").read_text(encoding="utf-8")
_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "producto_id": {"type": "string"},
        "presentacion": {"type": "string", "enum": ["frasco", "decant"]},
        "cantidad": {"type": "integer"},
    },
    "required": ["producto_id", "presentacion", "cantidad"],
}

TOOLS = [
    {"name": "cotizar",
     "description": "Calcula el total real (envío y promos aplicados) antes de cerrar. Único que decide el precio.",
     "input_schema": {"type": "object", "properties": {
         "items": {"type": "array", "items": _ITEM_SCHEMA},
         "metodo_envio": {"type": "string", "enum": ["caribe_tours", "delivery_gsd"]}},
         "required": ["items"]}},
    {"name": "registrar_pedido",
     "description": "Registra el pedido al confirmar nombre, dirección y teléfono (antes del pago).",
     "input_schema": {"type": "object", "properties": {
         "items": {"type": "array", "items": _ITEM_SCHEMA},
         "nombre": {"type": "string"}, "direccion": {"type": "string"},
         "telefono": {"type": "string"}, "pago": {"type": "string"},
         "metodo_envio": {"type": "string", "enum": ["caribe_tours", "delivery_gsd"]}},
         "required": ["items", "nombre", "direccion", "telefono"]}},
    {"name": "enviar_datos_pago",
     "description": "Envía al cliente el mensaje literal con la cuenta. Tú nunca escribes el número.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "enviar_foto", "description": "Envía la foto real de un producto.",
     "input_schema": {"type": "object", "properties": {"producto_id": {"type": "string"}},
                      "required": ["producto_id"]}},
    {"name": "enviar_catalogo", "description": "Envía el catálogo (PDF).",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "escalar_a_humano", "description": "Pasa la conversación al encargado.",
     "input_schema": {"type": "object", "properties": {"motivo": {"type": "string"}},
                      "required": ["motivo"]}},
]


def build_system(tenant: Tenant, productos: dict) -> str:
    catalogo = "\n".join(
        f"- id: {pid} | {p['nombre']} | {p['tipo']} | parecido a: {p['parecido_a']} | "
        f"notas: {p['notas']} | frasco RD${p['precio_frasco']} "
        f"(stock: {p['stock_frasco'] or 'AGOTADO'}) | decant RD${p['precio_decant']} "
        f"(stock: {p['stock_decant'] or 'AGOTADO'})"
        for pid, p in productos.items()
    )
    e = tenant.envio_config
    envio = (f"Caribe Tours/Vimenca RD${e['costo']}; gratis en compras de RD${e['gratis_desde']}+; "
             f"delivery GSD RD${e['delivery_gsd']}.")
    d = tenant.descuento_config
    descuento = (f"precios fijos; en {d['min_frascos']}+ frascos, RD${d['monto']} menos"
                 f"{' o envío gratis' if d.get('o_envio_gratis') else ''}. Más que eso, escalar.")
    return (PROMPT_TEMPLATE
            .replace("{{NOMBRE_NEGOCIO}}", tenant.nombre)
            .replace("{{RUBRO}}", tenant.rubro)
            .replace("{{CATALOGO}}", catalogo)
            .replace("{{ENVIO}}", envio)
            .replace("{{PAGO}}", tenant.pago_config)
            .replace("{{CUENTA}}", "(la manda el sistema con enviar_datos_pago; no la escribas tú)")
            .replace("{{POLITICA_DESCUENTO}}", descuento)
            .replace("{{INFO_EXTRA}}", tenant.info_extra or "—"))


class ToolContext:
    """Lo que las tools necesitan para ejecutar efectos reales."""
    def __init__(self, session, tenant: Tenant, cliente_wa: str):
        self.session, self.tenant, self.cliente_wa = session, tenant, cliente_wa
        self.escalado = False
        self.pedido_registrado = None


async def _ejecutar_tool(ctx: ToolContext, name: str, args: dict) -> dict:
    if name == "cotizar":
        return cotizar_db(ctx.session, ctx.tenant, args.get("items", []),
                          args.get("metodo_envio", "caribe_tours"))
    if name == "registrar_pedido":
        r = registrar_pedido(ctx.session, ctx.tenant, ctx.cliente_wa, args.get("items", []),
                             args.get("nombre", ""), args.get("direccion", ""),
                             args.get("telefono", ""), args.get("pago", ""),
                             args.get("metodo_envio", "caribe_tours"))
        if "order_id" in r:
            ctx.pedido_registrado = r
        return r
    if name == "enviar_datos_pago":
        await wa.send_text(ctx.tenant, ctx.cliente_wa, ctx.tenant.cuenta_mensaje)  # LITERAL
        return {"ok": True, "nota": "cuenta enviada por el sistema"}
    if name == "enviar_foto":
        p = productos_de(ctx.session, ctx.tenant.id).get(args.get("producto_id"))
        if not p:
            return {"error": f"producto desconocido: {args.get('producto_id')}"}
        if not p.get("foto_url"):
            return {"error": "sin foto"}
        await wa.send_image(ctx.tenant, ctx.cliente_wa, p["foto_url"], caption=p["nombre"])
        return {"ok": True}
    if name == "enviar_catalogo":
        if not ctx.tenant.catalogo_pdf_url:
            return {"error": "este negocio no tiene catálogo PDF cargado"}
        await wa.send_document(ctx.tenant, ctx.cliente_wa, ctx.tenant.catalogo_pdf_url)
        return {"ok": True}
    if name == "escalar_a_humano":
        ctx.escalado = True
        return {"ok": True, "motivo": args.get("motivo", "")}
    return {"error": f"tool desconocida: {name}"}


async def ejecutar_tool(ctx: ToolContext, name: str, args: dict) -> dict:
    try:
        return await _ejecutar_tool(ctx, name, args)
    except Exception as e:  # la excepción vuelve como tool_result, no tumba el turno
        log.exception("tool %s falló", name)
        return {"error": f"{type(e).__name__}: {e}"}


async def responder(ctx: ToolContext, history: list, user_text: str) -> str:
    """history = [{role, content: str}] persistido. El loop usa una copia local."""
    productos = productos_de(ctx.session, ctx.tenant.id)
    system = build_system(ctx.tenant, productos)
    work = [{"role": m["role"], "content": m["content"]} for m in history[-HISTORY_WINDOW:]]
    work.append({"role": "user", "content": user_text})

    def _call(messages):
        return claude.messages.create(model=MODEL_BRAIN, max_tokens=1024,
                                      system=system, tools=TOOLS, messages=messages)

    msg = await asyncio.to_thread(_call, work)
    for _ in range(8):  # tope de iteraciones de tools por turno
        if msg.stop_reason != "tool_use":
            break
        results = []
        for block in msg.content:
            if block.type == "tool_use":
                out = await ejecutar_tool(ctx, block.name, block.input)
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": json.dumps(out, ensure_ascii=False)})
        work.append({"role": "assistant", "content": msg.content})  # bloques crudos: SOLO local
        work.append({"role": "user", "content": results})
        msg = await asyncio.to_thread(_call, work)

    return "".join(b.text for b in msg.content if b.type == "text").strip()
