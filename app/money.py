"""
Capa determinística — LA AUTORIDAD DEL DINERO.
El LLM conversa; este módulo decide precios, envío, promos y stock. Si algo no cuadra,
devuelve {"error": ...} y el LLM se corrige; nunca improvisa el número.

`cotizar` es PURA (recibe dicts, no toca DB) para que sea trivial de testear.

── Formato de envio_cfg ──────────────────────────────────────────────────
Nuevo formato (configurable por el dueño):
{
  "metodos": [
    {"id": "retiro",   "tipo": "retiro",  "nombre": "Retiro en tienda",   "costo": 0},
    {"id": "fijo",     "tipo": "fijo",    "nombre": "Envío estándar",     "costo": 250},
    {"id": "gsd",      "tipo": "zona",    "nombre": "Gran Santo Domingo", "costo": 200},
    {"id": "santiago", "tipo": "zona",    "nombre": "Santiago",           "costo": 300}
  ],
  "gratis_desde": 5000,        # 0 o ausente = sin envío gratis por monto
  "gratis_activo": true        # switch del dueño
}
Formato VIEJO (se sigue soportando): {costo, gratis_desde, delivery_gsd}

── Formato de descuento_cfg ──────────────────────────────────────────────
Nuevo: {"promos": [ {id, tipo, activo, ...}, ... ]}
  "cantidad_frascos": {min_frascos, monto?, envio_gratis?}
  "monto_minimo":     {minimo, monto?, porcentaje?, envio_gratis?}
  "porcentaje":       {porcentaje}
Formato VIEJO: {min_frascos, monto, o_envio_gratis}
"""
from collections import Counter


def _norm_envio(cfg: dict) -> dict:
    if "metodos" in cfg:
        return cfg
    metodos = [{"id": "fijo", "tipo": "fijo", "nombre": "Envío estándar",
                "costo": cfg.get("costo", 0)}]
    if "delivery_gsd" in cfg:
        metodos.append({"id": "delivery_gsd", "tipo": "zona",
                        "nombre": "Delivery GSD", "costo": cfg["delivery_gsd"]})
    return {"metodos": metodos, "gratis_desde": cfg.get("gratis_desde", 0),
            "gratis_activo": cfg.get("gratis_desde", 0) > 0}


def _norm_promos(cfg: dict) -> list:
    if "promos" in cfg:
        return cfg["promos"]
    if cfg.get("min_frascos"):
        return [{"id": "promo_frascos", "tipo": "cantidad_frascos", "activo": True,
                 "min_frascos": cfg["min_frascos"], "monto": cfg.get("monto", 0),
                 "envio_gratis": cfg.get("o_envio_gratis", False)}]
    return []


def _resolver_envio(envio_cfg: dict, subtotal: int, metodo_envio: str):
    cfg = _norm_envio(envio_cfg)
    metodos = {m["id"]: m for m in cfg["metodos"]}
    if metodo_envio in (None, "", "auto"):
        elegido = next((m for m in cfg["metodos"] if m["tipo"] != "retiro"),
                       cfg["metodos"][0] if cfg["metodos"] else None)
    else:
        elegido = metodos.get(metodo_envio)
    if not elegido:
        return ("error", f"método de envío desconocido: {metodo_envio}")
    if elegido["tipo"] == "retiro":
        return (0, elegido, False)
    gratis = bool(cfg.get("gratis_activo") and cfg.get("gratis_desde", 0) > 0
                  and subtotal >= cfg["gratis_desde"])
    return (0 if gratis else elegido["costo"], elegido, gratis)


def _opciones_promo(promos: list, subtotal: int, frascos: int, base_envio: int):
    opciones = [("ninguna", subtotal + base_envio, base_envio, 0)]
    for p in promos:
        if not p.get("activo", True):
            continue
        t = p.get("tipo")
        nombre = p.get("id", t)
        if t == "cantidad_frascos" and frascos >= p.get("min_frascos", 99):
            monto = p.get("monto", 0)
            if monto:
                opciones.append((nombre, subtotal - monto + base_envio, base_envio, monto))
            if p.get("envio_gratis"):
                opciones.append((nombre + "_envio", subtotal, 0, base_envio))
        elif t == "monto_minimo" and subtotal >= p.get("minimo", 10**9):
            monto = p.get("monto", 0)
            pct = p.get("porcentaje", 0)
            desc = monto + (subtotal * pct // 100)
            if desc:
                opciones.append((nombre, subtotal - desc + base_envio, base_envio, desc))
            if p.get("envio_gratis"):
                opciones.append((nombre + "_envio", subtotal, 0, base_envio))
        elif t == "porcentaje":
            pct = p.get("porcentaje", 0)
            desc = subtotal * pct // 100
            if desc:
                opciones.append((nombre, subtotal - desc + base_envio, base_envio, desc))
    return opciones


def cotizar(productos: dict, envio_cfg: dict, descuento_cfg: dict, items: list,
            metodo_envio: str = "auto", aplicar_promo: str = "auto") -> dict:
    if not items:
        return {"error": "carrito vacío"}

    subtotal, frascos, detalle = 0, 0, []
    acumulado = Counter()

    for it in items:
        pid = it.get("producto_id")
        p = productos.get(pid)
        if not p:
            return {"error": f"producto desconocido: {pid}"}
        try:
            cant = int(it.get("cantidad", 1))
        except (TypeError, ValueError):
            return {"error": f"cantidad inválida: {it.get('cantidad')!r}"}
        if cant < 1:
            return {"error": f"cantidad inválida: {cant}"}
        pres = it.get("presentacion")
        if pres not in ("frasco", "decant"):
            return {"error": f"presentacion inválida: {pres}"}

        acumulado[(pid, pres)] += cant
        stock = p["stock_frasco"] if pres == "frasco" else p["stock_decant"]
        if acumulado[(pid, pres)] > stock:
            return {"error": f"stock insuficiente: {p['nombre']} ({pres}), quedan {stock}"}

        if pres == "frasco":
            precio, frascos = p["precio_frasco"], frascos + cant
        else:
            precio = p["precio_decant"]
        subtotal += precio * cant
        detalle.append({"producto": p["nombre"], "presentacion": pres,
                        "cantidad": cant, "precio": precio})

    env = _resolver_envio(envio_cfg, subtotal, metodo_envio)
    if env[0] == "error":
        return {"error": env[1]}
    base_envio, metodo_dict, _gratis = env

    promos = _norm_promos(descuento_cfg)
    opciones = _opciones_promo(promos, subtotal, frascos, base_envio)
    if aplicar_promo != "auto":
        filtradas = [o for o in opciones if o[0].startswith(aplicar_promo)]
        opciones = filtradas or opciones
    promo, total, envio, descuento = min(opciones, key=lambda o: o[1])

    cfg_n = _norm_envio(envio_cfg)
    gratis_activo = cfg_n.get("gratis_activo") and cfg_n.get("gratis_desde", 0) > 0
    falta = max(0, cfg_n["gratis_desde"] - subtotal) if (gratis_activo and envio > 0) else 0

    return {
        "detalle": detalle,
        "subtotal": subtotal,
        "envio": envio,
        "metodo_envio": metodo_dict["nombre"],
        "descuento": descuento,
        "promo_aplicada": None if promo == "ninguna" else promo,
        "total": total,
        "falta_para_envio_gratis": falta,
        "metodos_envio_disponibles": [
            {"id": m["id"], "nombre": m["nombre"], "tipo": m["tipo"], "costo": m["costo"]}
            for m in cfg_n["metodos"]],
    }


def agregar_items(items: list) -> Counter:
    acc = Counter()
    for it in items:
        acc[(it["producto_id"], it["presentacion"])] += int(it.get("cantidad", 1))
    return acc
