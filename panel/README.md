# Strouv · Panel (con autenticación)

Panel web multi-usuario para configurar el bot de ventas. Dos roles:

- **super_admin** (tú): crea negocios, crea la cuenta de cada dueño, ve métricas globales.
- **owner** (dueño de tienda): entra con su cuenta y gestiona SOLO su negocio.

App **Next.js** que consume la API del backend FastAPI (`/auth/*` y `/admin/*`), protegida
con JWT. La identidad y los permisos salen del token verificado en el servidor: un owner no
puede tocar otro negocio aunque manipule la URL.

## Primera vez (orden importa)

```bash
# 1) Backend (carpeta Strouv/) — crea tu super-admin y siembra Royal Oud de prueba
python -m app.bootstrap_admin tu@correo.com TuClaveSegura123
python -m app.seed
uvicorn app.main:app --reload          # http://localhost:8000

# 2) Panel (carpeta Strouv/panel/)
npm install
cp .env.local.example .env.local
npm run dev                            # http://localhost:3000
```

Entra en http://localhost:3000 con el correo/clave del super-admin.

## Flujo típico

1. Entras como super-admin → **Negocios** → "Nuevo negocio" (nombre y rubro).
2. En ese negocio → "Crear cuenta de dueño" (correo + contraseña temporal).
3. Le pasas esas credenciales al dueño. Él entra y ve solo su panel: Catálogo, Pedidos, Configuración.
4. El dueño (o tú) completa su configuración: WhatsApp, envío, pago, descuentos.

## Pantallas

**super-admin:** Resumen global · Negocios (alta de clientes y sus cuentas).
**owner:** Resumen (su embudo) · Catálogo · Pedidos · Configuración.

## Recuperación de contraseña

"¿Olvidaste tu contraseña?" → se envía un enlace al correo. **Sin SMTP configurado**, el
enlace se imprime en la consola del backend (útil en desarrollo). Para correo real, configura
`SMTP_*` en el `.env` del backend.

## Seguridad — lo que ya está y lo que falta

Hecho: contraseñas con bcrypt, sesiones JWT (1 semana), aislamiento por tenant en cada query,
roles, recuperación con token de un solo uso que expira en 1 hora.

Pendiente para producción (v2):
- **HTTPS obligatorio** y `JWT_SECRET` fuerte en el `.env` (no el de desarrollo).
- **Registro público** de dueños (hoy solo el super-admin crea cuentas; la pieza ya existe).
- Mover el token de `sessionStorage` a cookie httpOnly si quieres resistencia a XSS.
- Rate-limiting en login/forgot.

## Diseño

Negro violáceo + morado Strouv, gradiente morado→magenta como firma. Space Grotesk (display)
+ Inter (texto). Animaciones medidas con Framer Motion; respeta prefers-reduced-motion.
