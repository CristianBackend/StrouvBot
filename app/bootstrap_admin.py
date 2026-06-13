"""
Crea el primer super-admin (tú). Alguien tiene que ser el primero y no puede haber un
botón público para eso. Correr una vez:

    python -m app.bootstrap_admin tu@correo.com TuClaveSegura123

Si el correo ya existe, no hace nada.
"""
import sys

from .models import SessionLocal, User, init_db
from .security import hash_password


def run(email: str, password: str, nombre: str = "Admin"):
    if len(password) < 8:
        print("La contraseña debe tener al menos 8 caracteres.")
        return
    init_db()
    s = SessionLocal()
    try:
        if s.query(User).filter(User.email == email.lower()).first():
            print(f"Ya existe un usuario con {email}.")
            return
        u = User(email=email.lower(), password_hash=hash_password(password),
                 nombre=nombre, rol="super_admin", tenant_id=None)
        s.add(u)
        s.commit()
        print(f"Super-admin creado: {email}")
    finally:
        s.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python -m app.bootstrap_admin <email> <password> [nombre]")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "Admin")
