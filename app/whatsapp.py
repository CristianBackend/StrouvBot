"""Meta Cloud API directo (sin BSP). Cada tenant usa su propio wa_token y phone_id."""
import logging

import httpx

from .config import WA_API_VERSION

log = logging.getLogger("strouv.wa")
GRAPH = f"https://graph.facebook.com/{WA_API_VERSION}"


async def _post(tenant, payload: dict):
    url = f"{GRAPH}/{tenant.wa_phone_id}/messages"
    headers = {"Authorization": f"Bearer {tenant.wa_token}"}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, json=payload, headers=headers)
        if r.status_code >= 300:
            log.error("WA send failed %s: %s", r.status_code, r.text)
        return r


async def send_text(tenant, to: str, text: str):
    await _post(tenant, {"messaging_product": "whatsapp", "to": to,
                         "type": "text", "text": {"body": text}})


async def send_image(tenant, to: str, image_url: str, caption: str = ""):
    await _post(tenant, {"messaging_product": "whatsapp", "to": to, "type": "image",
                         "image": {"link": image_url, **({"caption": caption} if caption else {})}})


async def send_document(tenant, to: str, doc_url: str, filename: str = "catalogo.pdf"):
    await _post(tenant, {"messaging_product": "whatsapp", "to": to, "type": "document",
                         "document": {"link": doc_url, "filename": filename}})


def parse_webhook(body: dict):
    """
    Payload de Meta -> lista de (phone_id, wa_from, message_id, texto, tipo).
    tipo: 'text' | 'image' | otro. Para imágenes (comprobantes) texto va vacío.
    """
    out = []
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            phone_id = value.get("metadata", {}).get("phone_number_id")
            for msg in value.get("messages", []) or []:
                tipo = msg.get("type")
                texto = msg.get("text", {}).get("body", "") if tipo == "text" else ""
                out.append((phone_id, msg.get("from"), msg.get("id"), texto, tipo))
    return out
