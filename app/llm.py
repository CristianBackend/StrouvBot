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
from .money import _norm_envio  # normalizador autoritativo de envio_config (viejo y nuevo)
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

def _metodo_envio_schema(tenant: Tenant):
    """Schema de metodo_envio según el modo de envío del tenant.

    - zonas: enum con los ids REALES de las zonas (si se hardcodea, la API obliga al modelo a
      mandar ids inexistentes y cotizar() falla → el bot escala).
    - distancia: el envío sale del pin del cliente (lo resuelve el backend), el modelo no elige
      zona; solo puede pedir 'retiro' si está activo. Devuelve None si no hay método que elegir.
    """
    cfg = tenant.envio_config or {}
    if cfg.get("modo") == "distancia":
        if (cfg.get("retiro") or {}).get("activo"):
            return {"type": "string", "enum": ["retiro"],
                    "description": "déjalo VACÍO para envío a domicilio (se calcula por la ubicación "
                                   "que comparte el cliente); 'retiro' solo si retira en tienda"}
        return None  # sin retiro: el envío es 100% por ubicación, no hay nada que elegir
    cfg_n = _norm_envio(cfg)
    ids = [m["id"] for m in cfg_n.get("metodos", []) if m.get("id")]
    schema = {"type": "string",
              "description": "id de la zona/método de envío del negocio (ver 'Envío' en el system)"}
    if ids:  # un enum vacío es inválido para la API; sin ids, dejarlo string libre
        schema["enum"] = ids
    return schema


def build_tools(tenant: Tenant) -> list:
    """Tools por-tenant. metodo_envio refleja el modo de envío; se omite si no aplica."""
    metodo_envio = _metodo_envio_schema(tenant)
    cotizar_props = {"items": {"type": "array", "items": _ITEM_SCHEMA}}
    reg_props = {"items": {"type": "array", "items": _ITEM_SCHEMA},
                 "nombre": {"type": "string"}, "direccion": {"type": "string"},
                 "telefono": {"type": "string"}, "pago": {"type": "string"}}
    if metodo_envio is not None:
        cotizar_props["metodo_envio"] = metodo_envio
        reg_props["metodo_envio"] = metodo_envio
    return [
        {"name": "cotizar",
         "description": "Calcula el total real (envío y promos aplicados) antes de cerrar. Único que decide el precio.",
         "input_schema": {"type": "object", "properties": cotizar_props,
                          "required": ["items"]}},
        {"name": "registrar_pedido",
         "description": "Registra el pedido al confirmar nombre, dirección y teléfono (antes del pago).",
         "input_schema": {"type": "object", "properties": reg_props,
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
    e = tenant.envio_config or {}
    if e.get("modo") == "distancia":
        tramos = []
        for r in e.get("rangos", []):
            tope = r.get("hasta_km")
            etiqueta = f"hasta {tope} km" if tope is not None else "más lejos"
            tramos.append(f"{etiqueta}: RD${r.get('costo', 0)}")
        envio = ("Envío a domicilio por distancia (" + "; ".join(tramos) + ")") if tramos else "Envío por distancia"
        if (e.get("retiro") or {}).get("activo"):
            envio += f". {(e['retiro']).get('nombre', 'Retiro en tienda')} gratis"
        if e.get("gratis_activo") and e.get("gratis_desde", 0) > 0:
            envio += f". Envío gratis en compras de RD${e['gratis_desde']}+"
        envio += (". El envío se calcula con la ubicación que comparte el cliente (pin de WhatsApp); "
                  "el sistema da el costo al cotizar.")
    elif e.get("metodos"):
        partes = []
        for m in e["metodos"]:
            if m.get("tipo") == "retiro":
                partes.append(f"{m['nombre']} (gratis)")
            else:
                partes.append(f"{m['nombre']} RD${m.get('costo', 0)}")
        envio = "; ".join(partes)
        if e.get("gratis_activo") and e.get("gratis_desde", 0) > 0:
            envio += f". Envío gratis en compras de RD${e['gratis_desde']}+"
        envio += ". El cliente dice su dirección; ubícalo en la zona correcta y CONFIRMA el costo antes de cobrar."
    else:
        # formato viejo (retrocompatible)
        envio = (f"Envío RD${e.get('costo', 0)}; gratis en compras de RD${e.get('gratis_desde', 0)}+; "
                 f"delivery GSD RD${e.get('delivery_gsd', 0)}.")

    d = tenant.descuento_config or {}
    if d.get("promos") is not None:
        activas = [p for p in d.get("promos", []) if p.get("activo", True)]
        if activas:
            desc_partes = []
            for p in activas:
                t = p.get("tipo")
                if t == "cantidad_frascos":
                    extra = f"RD${p.get('monto', 0)} menos" if p.get("monto") else ""
                    if p.get("envio_gratis"):
                        extra += (" o " if extra else "") + "envío gratis"
                    desc_partes.append(f"en {p.get('min_frascos', 2)}+ frascos: {extra}")
                elif t == "monto_minimo":
                    extra = f"{p.get('porcentaje', 0)}% menos" if p.get("porcentaje") else f"RD${p.get('monto', 0)} menos"
                    desc_partes.append(f"en compras de RD${p.get('minimo', 0)}+: {extra}")
                elif t == "porcentaje":
                    desc_partes.append(f"{p.get('porcentaje', 0)}% de descuento general")
            descuento = "; ".join(desc_partes) + ". Más que eso, escalar."
        else:
            descuento = "Precios fijos, sin promociones activas. Cualquier rebaja extra, escalar."
    else:
        # formato viejo (retrocompatible)
        descuento = (f"precios fijos; en {d.get('min_frascos', 99)}+ frascos, RD${d.get('monto', 0)} menos"
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
                          args.get("metodo_envio", "auto"), cliente_wa=ctx.cliente_wa)
    if name == "registrar_pedido":
        r = registrar_pedido(ctx.session, ctx.tenant, ctx.cliente_wa, args.get("items", []),
                             args.get("nombre", ""), args.get("direccion", ""),
                             args.get("telefono", ""), args.get("pago", ""),
                             args.get("metodo_envio", "auto"))
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
    # DIAGNÓSTICO: loguea entrada/salida de cada tool. args puede traer PII (nombre/teléfono);
    # recortar este log una vez identificado el bug del cierre.
    log.info("tool ► %s args=%s", name, args)
    try:
        out = await _ejecutar_tool(ctx, name, args)
        if isinstance(out, dict) and "error" in out:
            log.warning("tool %s devolvió error (recuperable): %s", name, out["error"])
        else:
            log.info("tool %s OK", name)
        return out
    except Exception as e:  # la excepción vuelve como tool_result, no tumba el turno
        log.exception("tool %s LANZÓ excepción (args=%s)", name, args)
        return {"error": f"{type(e).__name__}: {e}"}


async def responder(ctx: ToolContext, history: list, user_text: str) -> str:
    """history = [{role, content: str}] persistido. El loop usa una copia local."""
    productos = productos_de(ctx.session, ctx.tenant.id)
    system = build_system(ctx.tenant, productos)
    tools = build_tools(ctx.tenant)  # enum de metodo_envio con las zonas reales de ESTE tenant
    work = [{"role": m["role"], "content": m["content"]} for m in history[-HISTORY_WINDOW:]]
    work.append({"role": "user", "content": user_text})

    def _call(messages):
        return claude.messages.create(model=MODEL_BRAIN, max_tokens=1024,
                                      system=system, tools=tools, messages=messages)

    async def _llamar_modelo(messages, paso):
        # DIAGNÓSTICO: aísla los fallos de Anthropic (lo único en responder que dispara el
        # fallback de I2). Loguea el paso exacto y re-lanza para no cambiar el comportamiento.
        try:
            return await asyncio.to_thread(_call, messages)
        except Exception:
            log.exception("Anthropic messages.create reventó en '%s' (cliente %s, %d msgs)",
                          paso, ctx.cliente_wa, len(messages))
            raise

    msg = await _llamar_modelo(work, "llamada inicial")
    for i in range(8):  # tope de iteraciones de tools por turno
        log.info("loop iter %d (cliente %s): stop_reason=%s, bloques=%s",
                 i, ctx.cliente_wa, msg.stop_reason, [b.type for b in msg.content])
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
        msg = await _llamar_modelo(work, f"seguimiento tras tools (iter {i})")
    else:
        log.warning("loop agotó las 8 iteraciones sin texto final (cliente %s, stop_reason=%s)",
                    ctx.cliente_wa, msg.stop_reason)

    return "".join(b.text for b in msg.content if b.type == "text").strip()