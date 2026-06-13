import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./strouv.db")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "cambia-esto")
WA_API_VERSION = os.environ.get("WA_API_VERSION", "v21.0")

# App Secret de la app de Meta. Sirve para verificar la firma X-Hub-Signature-256 de los
# webhooks entrantes: sin esto, cualquiera podría forjar mensajes de cliente o comandos del
# dueño (PAGADO/CANCELADO). Es a nivel de la app de Meta (común a todos los tenants), no de
# negocio. Si está vacío, el webhook NO verifica firma (solo aceptable en local/desarrollo).
META_APP_SECRET = os.environ.get("META_APP_SECRET", "")

# Secreto para firmar los JWT de sesión. EN PRODUCCIÓN pon uno largo y aleatorio en el .env.
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-cambialo-en-produccion")
JWT_SECRET_ES_DEFAULT = JWT_SECRET == "dev-secret-cambialo-en-produccion"

# URL pública del panel (para armar el link de recuperación de contraseña).
PANEL_URL = os.environ.get("PANEL_URL", "http://localhost:3000")

# Correo saliente (recuperación de contraseña). Si no se configura, el link se imprime en consola.
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "Strouv <no-reply@strouv.app>")

MODEL_BRAIN = os.environ.get("MODEL_BRAIN", "claude-fable-5")     # regateo, asesoría, cierre
MODEL_CHEAP = os.environ.get("MODEL_CHEAP", "claude-haiku-4-5")   # rutina/clasificación (ruteo de costo, opcional)

DEBOUNCE_SECONDS = float(os.environ.get("DEBOUNCE_SECONDS", "4"))  # ráfagas de WhatsApp
HISTORY_WINDOW = int(os.environ.get("HISTORY_WINDOW", "20"))       # últimos N mensajes al LLM
