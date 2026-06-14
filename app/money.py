"""
Capa determinística — LA AUTORIDAD DEL DINERO.
El LLM conversa; este módulo decide precios, envío, promos y stock. Si algo no cuadra,
devuelve {"error": ...} y el LLM se corrige; nunca improvisa el número.

`cotizar` es PURA (recibe dicts, no toca DB) para que sea trivial de testear.

── Formato de envio_cfg ──────────────────────────────────────────────────
El campo "modo" discrimina cómo se cobra el envío (default "zonas", retrocompat):

modo "zonas" (formato actual; el dueño elige métodos/zonas manuales):
{
  "modo": "zonas",             # opcional; si falta, se asume "zonas"
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

modo "distancia" (geolocalización; precio por tramo de distancia en línea recta):
{
  "modo": "distancia",
  "origen": {"lat": 18.4861, "lng": -69.9312},     # ubicación del negocio
  "rangos": [                                       # ordenados por hasta_km
    {"hasta_km": 8,    "costo": 150},
    {"hasta_km": 20,   "costo": 250},
    {"hasta_km": null, "costo": 400}                # null = franja abierta (cobra máx);
  ],                                                #   si todas tienen tope -> fuera_de_cobertura
  "retiro": {"activo": true, "nombre": "Retiro en tienda"},
  "gratis_desde": 5000,
  "gratis_activo": true
}
La ubicación del cliente (lat/lng) la resuelve el backend (pin de WhatsApp o geocodificación)
y se pasa a cotizar() como `ubicacion`; el modelo NUNCA pasa coordenadas. Señales de error que
cotizar() puede devolver en este modo (para que el prompt las maneje): "envio_no_configurado",
"falta_ubicacion", "ubicacion_imprecisa", "fuera_de_cobertura", "retiro_no_disponible".

── Formato de descuento_cfg ──────────────────────────────────────────────
Nuevo: {"promos": [ {id, tipo, activo, ...}, ... ]}
  "cantidad_frascos": {min_frascos, monto?, envio_gratis?}
  "monto_minimo":     {minimo, monto?, porcentaje?, envio_gratis?}
  "porcentaje":       {porcentaje}
Formato VIEJO: {min_frascos, monto, o_envio_gratis}
"""
import math
from collections import Counter


def _norm_envio(cfg: dict) -> dict:
    if cfg.get("modo") == "distancia":
        return cfg  # el modo distancia no usa "metodos"; se resuelve aparte
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


# ── Modo distancia (geolocalización) ──────────────────────────────────────
def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distancia en línea recta (km) entre dos puntos. Pura; gratis (sin API)."""
    radio_km = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * radio_km * math.asin(math.sqrt(a))


def _elegir_rango(rangos: list, dist_km: float):
    """Primer rango cuyo hasta_km cubre la distancia. hasta_km null = franja abierta (va al
    final). Si todas tienen tope y la distancia los excede -> None (fuera de cobertura)."""
    ordenados = sorted(rangos, key=lambda r: (r.get("hasta_km") is None, r.get("hasta_km") or 0))
    for r in ordenados:
        tope = r.get("hasta_km")
        if tope is None or dist_km <= tope:
            return r
    return None


def _metodos_distancia(cfg: dict) -> list:
    """Lista informativa de opciones de envío en modo distancia (retiro + tramos)."""
    out = []
    retiro = cfg.get("retiro") or {}
    if retiro.get("activo"):
        out.append({"id": "retiro", "nombre": retiro.get("nombre", "Retiro en tienda"),
                    "tipo": "retiro", "costo": 0})
    for r in cfg.get("rangos", []):
        tope = r.get("hasta_km")
        nombre = f"hasta {tope} km" if tope is not None else "más lejos"
        out.append({"id": f"rango_{tope}", "nombre": nombre, "tipo": "distancia",
                    "costo": r.get("costo", 0)})
    return out


def _resolver_envio_distancia(cfg: dict, subtotal: int, metodo_envio: str, ubicacion):
    """Igual contrato que _resolver_envio: ('error', señal) | (costo, metodo_dict, gratis)."""
    retiro = cfg.get("retiro") or {}
    if metodo_envio == "retiro":
        if not retiro.get("activo"):
            return ("error", "retiro_no_disponible")
        return (0, {"nombre": retiro.get("nombre", "Retiro en tienda"), "tipo": "retiro"}, False)

    origen = cfg.get("origen") or {}
    rangos = cfg.get("rangos") or []
    if origen.get("lat") is None or origen.get("lng") is None or not rangos:
        return ("error", "envio_no_configurado")  # el dueño aún no terminó de configurar

    if not ubicacion or ubicacion.get("lat") is None or ubicacion.get("lng") is None:
        return ("error", "falta_ubicacion")        # el bot debe pedir el pin
    if ubicacion.get("precision") == "baja":
        return ("error", "ubicacion_imprecisa")    # geocodificación dudosa (F3); pedir pin

    dist = haversine(origen["lat"], origen["lng"], ubicacion["lat"], ubicacion["lng"])
    rango = _elegir_rango(rangos, dist)
    if rango is None:
        return ("error", "fuera_de_cobertura")

    gratis = bool(cfg.get("gratis_activo") and cfg.get("gratis_desde", 0) > 0
                  and subtotal >= cfg["gratis_desde"])
    tope = rango.get("hasta_km")
    metodo_dict = {"nombre": f"Envío (hasta {tope} km)" if tope is not None else "Envío (zona lejana)",
                   "tipo": "distancia", "distancia_km": round(dist, 1)}
    return (0 if gratis else rango.get("costo", 0), metodo_dict, gratis)


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
            metodo_envio: str = "auto", aplicar_promo: str = "auto", ubicacion=None) -> dict:
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

    modo = envio_cfg.get("modo", "zonas")
    if modo == "distancia":
        env = _resolver_envio_distancia(envio_cfg, subtotal, metodo_envio, ubicacion)
    else:
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

    if modo == "distancia":
        gratis_desde = envio_cfg.get("gratis_desde", 0)
        gratis_activo = envio_cfg.get("gratis_activo") and gratis_desde > 0
        metodos_disp = _metodos_distancia(envio_cfg)
    else:
        cfg_n = _norm_envio(envio_cfg)
        gratis_desde = cfg_n.get("gratis_desde", 0)
        gratis_activo = cfg_n.get("gratis_activo") and gratis_desde > 0
        metodos_disp = [{"id": m["id"], "nombre": m["nombre"], "tipo": m["tipo"], "costo": m["costo"]}
                        for m in cfg_n["metodos"]]
    falta = max(0, gratis_desde - subtotal) if (gratis_activo and envio > 0) else 0

    resultado = {
        "detalle": detalle,
        "subtotal": subtotal,
        "envio": envio,
        "metodo_envio": metodo_dict["nombre"],
        "descuento": descuento,
        "promo_aplicada": None if promo == "ninguna" else promo,
        "total": total,
        "falta_para_envio_gratis": falta,
        "metodos_envio_disponibles": metodos_disp,
    }
    if "distancia_km" in metodo_dict:
        resultado["distancia_km"] = metodo_dict["distancia_km"]
    return resultado


def agregar_items(items: list) -> Counter:
    acc = Counter()
    for it in items:
        acc[(it["producto_id"], it["presentacion"])] += int(it.get("cantidad", 1))
    return acc
