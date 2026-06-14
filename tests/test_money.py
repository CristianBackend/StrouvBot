"""
Acceptance criteria de la capa de dinero. Si algo de esto rompe, NO se despliega.
Corre: pytest -q
"""
import os

os.environ["DATABASE_URL"] = "sqlite://"  # in-memory, antes de importar app.*

import pytest
from sqlalchemy import text

from app.models import SessionLocal, init_db
from app.money import cotizar
from app.orders import registrar_pedido, productos_de
from app.seed import ROYAL, PRODUCTOS

# ── Fixture puro (mismos números que el seed) ────────────────────────────
PRODS = {
    "khamrah": {"nombre": "Lattafa Khamrah", "precio_frasco": 3800, "precio_decant": 550,
                "stock_frasco": 6, "stock_decant": 20},
    "asad": {"nombre": "Lattafa Asad", "precio_frasco": 2900, "precio_decant": 450,
             "stock_frasco": 4, "stock_decant": 15},
    "9pm": {"nombre": "Afnan 9pm", "precio_frasco": 2600, "precio_decant": 400,
            "stock_frasco": 0, "stock_decant": 12},
}
ENVIO = {"costo": 250, "gratis_desde": 5000, "delivery_gsd": 200}
DESC = {"min_frascos": 2, "monto": 200, "o_envio_gratis": True}


def q(items, **kw):
    return cotizar(PRODS, ENVIO, DESC, items, **kw)


def test_decant_simple():
    r = q([{"producto_id": "9pm", "presentacion": "decant", "cantidad": 1}])
    assert r["subtotal"] == 400 and r["envio"] == 250 and r["total"] == 650
    assert r["falta_para_envio_gratis"] == 4600 and r["promo_aplicada"] is None


def test_promo_aplicada_no_solo_reportada():
    r = q([{"producto_id": "khamrah", "presentacion": "frasco", "cantidad": 2}])
    # subtotal 7600 supera umbral 5000 -> envío gratis por monto; ADEMÁS promo de frascos -200
    assert r["subtotal"] == 7600 and r["envio"] == 0 and r["descuento"] == 200
    assert r["total"] == 7400 and r["promo_aplicada"].startswith("promo_frascos")


def test_producto_desconocido_es_error_no_silencio():
    r = q([{"producto_id": "fantasma", "presentacion": "frasco", "cantidad": 1}])
    assert "error" in r and "desconocido" in r["error"]


def test_agotado_es_error():
    r = q([{"producto_id": "9pm", "presentacion": "frasco", "cantidad": 1}])
    assert "error" in r and "stock insuficiente" in r["error"]


def test_cantidad_negativa_sin_descuento_infinito():
    r = q([{"producto_id": "khamrah", "presentacion": "frasco", "cantidad": -1}])
    assert "error" in r and "cantidad inválida" in r["error"]


def test_cantidad_basura_no_explota():
    r = q([{"producto_id": "khamrah", "presentacion": "frasco", "cantidad": "abc"}])
    assert "error" in r


def test_stock_agregado_no_por_linea():
    r = q([{"producto_id": "khamrah", "presentacion": "frasco", "cantidad": 4},
           {"producto_id": "khamrah", "presentacion": "frasco", "cantidad": 4}])
    assert "error" in r and "stock insuficiente" in r["error"]


def test_carrito_vacio():
    assert "error" in q([])


def test_presentacion_invalida():
    r = q([{"producto_id": "khamrah", "presentacion": "galon", "cantidad": 1}])
    assert "error" in r


def test_promo_forzada_respetada():
    r = q([{"producto_id": "asad", "presentacion": "frasco", "cantidad": 2}],
          aplicar_promo="promo_frascos")
    # subtotal 5800 supera umbral 5000 (envío gratis) + promo frascos -200 = 5600
    assert r["promo_aplicada"].startswith("promo_frascos") and r["total"] == 5600


# ── Capa DB: re-cotización y reserva atómica ─────────────────────────────
@pytest.fixture()
def session():
    init_db()
    s = SessionLocal()
    if not s.get(type(ROYAL), "royal_oud"):
        s.add(ROYAL)
        s.add_all(PRODUCTOS)
        s.commit()
    # restaurar stock entre tests
    s.execute(text("UPDATE products SET stock_frasco=6, stock_decant=20 WHERE id='khamrah'"))
    s.execute(text("UPDATE products SET stock_frasco=4 WHERE id='asad'"))
    s.commit()
    yield s
    s.close()


def test_registrar_pedido_recotiza_y_descuenta_stock(session):
    tenant = session.get(type(ROYAL), "royal_oud")
    r = registrar_pedido(session, tenant, "18290000000",
                         [{"producto_id": "khamrah", "presentacion": "frasco", "cantidad": 2}],
                         "Juan", "Santiago, Los Jardines #12", "8295551234")
    assert r["total"] == 7400 and r["estado"] == "pago_pendiente_verificacion"
    assert productos_de(session, "royal_oud")["khamrah"]["stock_frasco"] == 4


def test_carrera_por_el_ultimo_frasco(session):
    tenant = session.get(type(ROYAL), "royal_oud")
    session.execute(text("UPDATE products SET stock_frasco=1 WHERE id='asad'"))
    session.commit()
    item = [{"producto_id": "asad", "presentacion": "frasco", "cantidad": 1}]
    r1 = registrar_pedido(session, tenant, "1829111", item, "A", "dir", "tel")
    r2 = registrar_pedido(session, tenant, "1829222", item, "B", "dir", "tel")
    assert "order_id" in r1
    assert "error" in r2  # el segundo NO nace válido


# ── Capacidades nuevas: envío por zonas/retiro y promos múltiples ─────────
ENVIO_ZONAS = {
    "metodos": [
        {"id": "retiro", "tipo": "retiro", "nombre": "Retiro en tienda", "costo": 0},
        {"id": "gsd", "tipo": "zona", "nombre": "Gran Santo Domingo", "costo": 200},
        {"id": "santiago", "tipo": "zona", "nombre": "Santiago", "costo": 300},
        {"id": "resto", "tipo": "zona", "nombre": "Resto del país", "costo": 350},
    ],
    "gratis_desde": 5000, "gratis_activo": True,
}


def qz(items, **kw):
    return cotizar(PRODS, ENVIO_ZONAS, {"promos": []}, items, **kw)


def test_zona_gsd_cobra_su_precio():
    r = qz([{"producto_id": "9pm", "presentacion": "decant", "cantidad": 1}], metodo_envio="gsd")
    assert r["envio"] == 200 and r["metodo_envio"] == "Gran Santo Domingo"


def test_zona_santiago_mas_cara_que_gsd():
    decant = [{"producto_id": "9pm", "presentacion": "decant", "cantidad": 1}]
    assert qz(decant, metodo_envio="santiago")["envio"] == 300
    assert qz(decant, metodo_envio="gsd")["envio"] == 200  # GSD nunca paga lo de Santiago


def test_retiro_en_tienda_envio_cero():
    r = qz([{"producto_id": "khamrah", "presentacion": "decant", "cantidad": 1}], metodo_envio="retiro")
    assert r["envio"] == 0


def test_zona_desconocida_es_error():
    r = qz([{"producto_id": "9pm", "presentacion": "decant", "cantidad": 1}], metodo_envio="marte")
    assert "error" in r


def test_envio_gratis_por_monto_aplica_en_zona():
    # subtotal 7600 > 5000 -> envío gratis aunque sea zona Santiago
    r = qz([{"producto_id": "khamrah", "presentacion": "frasco", "cantidad": 2}], metodo_envio="santiago")
    assert r["envio"] == 0


def test_promo_por_monto_minimo():
    promos = {"promos": [{"id": "black", "tipo": "monto_minimo", "activo": True,
                          "minimo": 3000, "porcentaje": 10}]}
    # 1 frasco khamrah = 3800 -> 10% = 380 de descuento
    r = cotizar(PRODS, ENVIO_ZONAS, promos, [{"producto_id": "khamrah", "presentacion": "frasco", "cantidad": 1}], metodo_envio="gsd")
    assert r["descuento"] == 380 and r["total"] == 3800 - 380 + 200


def test_promo_porcentaje_general():
    promos = {"promos": [{"id": "promo5", "tipo": "porcentaje", "activo": True, "porcentaje": 5}]}
    r = cotizar(PRODS, ENVIO_ZONAS, promos, [{"producto_id": "9pm", "presentacion": "decant", "cantidad": 1}], metodo_envio="retiro")
    # decant 400, 5% = 20, retiro 0 -> 380
    assert r["descuento"] == 20 and r["total"] == 380


def test_promo_desactivada_no_aplica():
    promos = {"promos": [{"id": "off", "tipo": "porcentaje", "activo": False, "porcentaje": 50}]}
    r = cotizar(PRODS, ENVIO_ZONAS, promos, [{"producto_id": "khamrah", "presentacion": "frasco", "cantidad": 1}], metodo_envio="gsd")
    assert r["descuento"] == 0


def test_elige_promo_mas_favorable():
    # dos promos: 10% y monto fijo 200. Sobre 3800: 10%=380 gana sobre 200.
    promos = {"promos": [
        {"id": "pct", "tipo": "monto_minimo", "activo": True, "minimo": 0, "porcentaje": 10},
        {"id": "fijo", "tipo": "monto_minimo", "activo": True, "minimo": 0, "monto": 200},
    ]}
    r = cotizar(PRODS, ENVIO_ZONAS, promos, [{"producto_id": "khamrah", "presentacion": "frasco", "cantidad": 1}], metodo_envio="retiro")
    assert r["descuento"] == 380  # eligió el mejor para el cliente


# ── F1: envío por distancia (geolocalización) ────────────────────────────
from app.money import haversine  # noqa: E402

ORIGEN = {"lat": 18.4861, "lng": -69.9312}  # Santo Domingo
# Offsets SOLO en latitud => distancia ≈ grados * 111.19 km, predecible:
CLIENTE_CERCA = {"lat": 18.5061, "lng": -69.9312}   # +0.02° ≈ 2.2 km   -> rango 0-8
CLIENTE_MEDIO = {"lat": 18.5861, "lng": -69.9312}   # +0.10° ≈ 11.1 km  -> rango 8-20
CLIENTE_LEJOS = {"lat": 18.7861, "lng": -69.9312}   # +0.30° ≈ 33.4 km  -> >20

ENVIO_DIST = {
    "modo": "distancia",
    "origen": ORIGEN,
    "rangos": [
        {"hasta_km": 8, "costo": 150},
        {"hasta_km": 20, "costo": 250},
        {"hasta_km": None, "costo": 400},   # franja abierta: cobra el máximo
    ],
    "retiro": {"activo": True, "nombre": "Retiro en tienda"},
    "gratis_desde": 5000, "gratis_activo": True,
}
# Igual pero con tope duro (sin franja abierta) -> fuera de cobertura si excede.
ENVIO_DIST_CAP = {**ENVIO_DIST, "rangos": ENVIO_DIST["rangos"][:2]}

DECANT = [{"producto_id": "9pm", "presentacion": "decant", "cantidad": 1}]  # subtotal 400


def qd(items, cfg=ENVIO_DIST, **kw):
    return cotizar(PRODS, cfg, {"promos": []}, items, **kw)


def test_haversine_un_grado_de_latitud():
    assert abs(haversine(0, 0, 1, 0) - 111.19) < 0.5  # ~111 km por grado de latitud


def test_distancia_rango_cercano():
    r = qd(DECANT, ubicacion=CLIENTE_CERCA)
    assert r["envio"] == 150 and r["total"] == 550
    assert "distancia_km" in r and r["distancia_km"] < 8


def test_distancia_rango_medio():
    r = qd(DECANT, ubicacion=CLIENTE_MEDIO)
    assert r["envio"] == 250 and 8 < r["distancia_km"] <= 20


def test_distancia_franja_abierta_cobra_maximo():
    r = qd(DECANT, ubicacion=CLIENTE_LEJOS)
    assert r["envio"] == 400 and r["distancia_km"] > 20


def test_distancia_tope_duro_fuera_de_cobertura():
    r = qd(DECANT, cfg=ENVIO_DIST_CAP, ubicacion=CLIENTE_LEJOS)
    assert r.get("error") == "fuera_de_cobertura"


def test_distancia_retiro_gratis():
    r = qd(DECANT, metodo_envio="retiro")
    assert r["envio"] == 0 and r["metodo_envio"] == "Retiro en tienda"


def test_distancia_retiro_no_disponible():
    cfg = {**ENVIO_DIST, "retiro": {"activo": False}}
    r = qd(DECANT, cfg=cfg, metodo_envio="retiro")
    assert r.get("error") == "retiro_no_disponible"


def test_distancia_falta_ubicacion():
    r = qd(DECANT)  # sin pin y sin retiro
    assert r.get("error") == "falta_ubicacion"


def test_distancia_ubicacion_imprecisa():
    r = qd(DECANT, ubicacion={**CLIENTE_CERCA, "precision": "baja"})
    assert r.get("error") == "ubicacion_imprecisa"


def test_distancia_sin_origen_no_configurado():
    cfg = {**ENVIO_DIST, "origen": {}}
    r = qd(DECANT, cfg=cfg, ubicacion=CLIENTE_CERCA)
    assert r.get("error") == "envio_no_configurado"


def test_distancia_envio_gratis_por_monto():
    # 2 frascos khamrah = 7600 > 5000 -> envío gratis aunque esté lejos
    r = qd([{"producto_id": "khamrah", "presentacion": "frasco", "cantidad": 2}],
           ubicacion=CLIENTE_LEJOS)
    assert r["envio"] == 0 and r["falta_para_envio_gratis"] == 0


def test_distancia_lista_metodos_disponibles():
    r = qd(DECANT, ubicacion=CLIENTE_CERCA)
    ids = {m["id"] for m in r["metodos_envio_disponibles"]}
    assert "retiro" in ids and any(i.startswith("rango_") for i in ids)


def test_modo_zonas_sigue_intacto_con_pin_ignorado():
    # un tenant de zonas no se ve afectado por pasar ubicacion (la ignora)
    r = cotizar(PRODS, ENVIO_ZONAS, {"promos": []}, DECANT,
                metodo_envio="gsd", ubicacion=CLIENTE_CERCA)
    assert r["envio"] == 200 and r["metodo_envio"] == "Gran Santo Domingo"
