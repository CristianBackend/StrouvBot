"""Seed del tenant de prueba Royal Oud. Correr: python -m app.seed"""
from .models import Product, SessionLocal, Tenant, init_db

ROYAL = Tenant(
    id="royal_oud", nombre="Royal Oud",
    rubro="tienda de perfumes árabes y de diseñador (frascos y decants)",
    wa_phone_id="REEMPLAZA_PHONE_ID", wa_token="REEMPLAZA_TOKEN",
    owner_wa="1809XXXXXXX",
    envio_config={
        "metodos": [
            {"id": "retiro", "tipo": "retiro", "nombre": "Retiro en tienda", "costo": 0},
            {"id": "gsd", "tipo": "zona", "nombre": "Gran Santo Domingo", "costo": 200},
            {"id": "santiago", "tipo": "zona", "nombre": "Santiago", "costo": 300},
            {"id": "resto", "tipo": "zona", "nombre": "Resto del país", "costo": 350},
        ],
        "gratis_desde": 5000, "gratis_activo": True,
    },
    pago_config="Transferencia, tPago, o efectivo contra entrega (solo GSD).",
    cuenta_mensaje=("Para el pago:\nBanreservas — Cuenta de Ahorros 960-123456-7\n"
                    "A nombre de Royal Oud\ntPago: 809-555-0000"),
    descuento_config={"promos": [
        {"id": "dos_frascos", "tipo": "cantidad_frascos", "activo": True,
         "min_frascos": 2, "monto": 200, "envio_gratis": True},
    ]},
    info_extra="Horario: lun-sáb 9am-7pm. Perfumes 100% originales.",
    catalogo_pdf_url="",
)

PRODUCTOS = [
    Product(id="khamrah", tenant_id="royal_oud", nombre="Lattafa Khamrah", tipo="Árabe",
            parecido_a="Angels' Share", notas="dulce, canela, dátiles",
            precio_frasco=3800, precio_decant=550, stock_frasco=6, stock_decant=20,
            foto_url="https://example.com/khamrah.jpg"),
    Product(id="asad", tenant_id="royal_oud", nombre="Lattafa Asad", tipo="Árabe",
            parecido_a="Sauvage Elixir", notas="pimienta, ámbar, fuerte",
            precio_frasco=2900, precio_decant=450, stock_frasco=4, stock_decant=15,
            foto_url="https://example.com/asad.jpg"),
    Product(id="9pm", tenant_id="royal_oud", nombre="Afnan 9pm", tipo="Árabe",
            parecido_a="Ultra Male", notas="dulce, lavanda, manzana",
            precio_frasco=2600, precio_decant=400, stock_frasco=0, stock_decant=12,
            foto_url="https://example.com/9pm.jpg"),
]

def run():
    init_db()
    s = SessionLocal()
    if not s.get(Tenant, "royal_oud"):
        s.add(ROYAL)
        s.add_all(PRODUCTOS)
        s.commit()
        print("Seed Royal Oud creado.")
    else:
        print("Royal Oud ya existe; nada que hacer.")
    s.close()

if __name__ == "__main__":
    run()
