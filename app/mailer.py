"""
Envío de correo. Si no hay SMTP configurado, imprime el contenido en consola — así en
desarrollo ves el link de recuperación sin montar un servidor de correo.
"""
import logging
import smtplib
from email.message import EmailMessage

from .config import (PANEL_URL, SMTP_FROM, SMTP_HOST, SMTP_PASS, SMTP_PORT, SMTP_USER)

log = logging.getLogger("strouv.mail")


def enviar_reset(email: str, raw_token: str):
    link = f"{PANEL_URL}/reset?token={raw_token}"
    cuerpo = (f"Recibimos una solicitud para restablecer tu contraseña de Strouv.\n\n"
              f"Abre este enlace para elegir una nueva (válido por 1 hora):\n{link}\n\n"
              f"Si no fuiste tú, ignora este correo.")
    if not SMTP_HOST:
        log.warning("SMTP no configurado — link de recuperación para %s:\n%s", email, link)
        print(f"\n[DEV] Link de recuperación para {email}:\n{link}\n")
        return
    msg = EmailMessage()
    msg["Subject"] = "Restablece tu contraseña · Strouv"
    msg["From"] = SMTP_FROM
    msg["To"] = email
    msg.set_content(cuerpo)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        if SMTP_USER:
            s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
