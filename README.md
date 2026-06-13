# Strouv — Bot vendedor por WhatsApp (multi-tenant)

El cliente escribe por WhatsApp; el bot asesora, regatea, cotiza, toma el pedido y da los
datos de pago. Una sola base de código sirve a muchos negocios.

**Regla de oro:** el LLM conversa; **el código es la autoridad del dinero**. Totales, cuenta,
stock y verificación de pago nunca dependen del criterio del modelo (ver `app/money.py` y
`tests/test_money.py` — esos tests son los acceptance criteria: si rompen, no se despliega).

## Estructura

```
app/
  money.py            cotizar() puro — precios, promos, stock (validado por tests)
  orders.py           registrar_pedido: re-cotiza + reserva stock ATÓMICA, cambiar_estado
  models.py           tenants, products, orders, conversations, processed_messages
  llm.py              cerebro (Fable) con tool-use; excepciones de tools no tumban el turno
  whatsapp.py         Meta Cloud API: enviar texto/imagen/PDF, parsear webhook
  main.py             FastAPI: webhook (200 inmediato, idempotencia, debounce),
                      comandos del dueño (PAGADO/DESPACHADO/CANCELADO <id>), notificaciones
  prompt_template.md  system prompt con {{huecos}} que se inyectan por tenant
  seed.py             tenant de prueba Royal Oud
migrations/001_init.sql
```

## Correr local

```bash
pip install -r requirements.txt
cp .env.example .env            # edita ANTHROPIC_API_KEY; local usa SQLite por defecto
python -m app.seed              # crea Royal Oud
pytest -q                       # 12 tests de la capa de dinero — deben pasar
uvicorn app.main:app --reload
```

Exponer el webhook en desarrollo: `ngrok http 8000` y registra `https://.../webhook` en Meta.

## Conectar WhatsApp (Meta Cloud API, sin BSP)

1. App en developers.facebook.com → producto WhatsApp → toma `phone_number_id` y un token
   permanente (System User).
2. Webhook: URL `https://tu-dominio/webhook`, verify token = `VERIFY_TOKEN` de tu `.env`,
   suscribe el campo `messages`.
3. Guarda `wa_phone_id`, `wa_token` y `owner_wa` en la fila del tenant. Cada negocio conecta
   **su propio número**; el tenant se resuelve por `phone_id` en cada mensaje entrante.

## Flujo de pago (v1, sin panel)

El pedido nace `pago_pendiente_verificacion`. Cuando se registra, el dueño recibe un WhatsApp;
verifica el comprobante con sus ojos y responde **`PAGADO 14`** (o `DESPACHADO 14` /
`CANCELADO 14`). El bot nunca confirma un pago por sí mismo.

## Desplegar (Railway / Fly / VPS)

- `DATABASE_URL` → Postgres (aplica `migrations/001_init.sql` o deja que `create_all` lo haga).
- Docker: `docker build -t strouv . && docker run -p 8000:8000 --env-file .env strouv`.
- **Un solo worker** por ahora: el debounce y la deduplicación de ráfagas viven en memoria
  del proceso. Para escalar horizontal, mueve buffers a Redis (TODO conocido).

## Agregar un tenant nuevo

Inserta una fila en `tenants` + sus `products`. Cero código: el prompt es fijo, la config cambia.

## TODOs conocidos (v2)

- Ruteo de costo: clasificar turnos rutinarios hacia `MODEL_CHEAP` (hoy todo va a Fable).
- Visión para comprobantes (OCR + match de monto) y para "¿tienen este?" + foto.
- Redis para debounce/buffers multi-worker; limpieza periódica de `processed_messages`.
- Comando del dueño para des-escalar ("BOT ON <cliente>") y devolverle la conversación al bot.

---

## Autenticación y panel (agregado)

El backend ahora expone auth (`/auth/*`) y administración (`/admin/*`) además del webhook.

```bash
python -m app.bootstrap_admin tu@correo.com TuClave123   # crea tu super-admin (una vez)
python -m app.seed                                        # tenant de prueba Royal Oud
uvicorn app.main:app --reload
```

Roles: `super_admin` (gestiona todo) y `owner` (su negocio). La identidad sale del JWT;
cada query admin filtra por el tenant del token. Variables nuevas en `.env`:
`JWT_SECRET` (ponlo fuerte en prod), `PANEL_URL`, y `SMTP_*` (opcional, para correo de
recuperación; sin ellas el link se imprime en consola).

El panel web vive en `panel/` (Next.js). Ver `panel/README.md`.
