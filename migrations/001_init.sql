-- Migración inicial (Postgres). Equivale a Base.metadata.create_all.
CREATE TABLE IF NOT EXISTS tenants (
  id TEXT PRIMARY KEY, nombre TEXT NOT NULL, rubro TEXT NOT NULL,
  wa_phone_id TEXT UNIQUE NOT NULL, wa_token TEXT NOT NULL, owner_wa TEXT NOT NULL,
  envio_config JSONB NOT NULL, pago_config TEXT NOT NULL, cuenta_mensaje TEXT NOT NULL,
  descuento_config JSONB NOT NULL, info_extra TEXT DEFAULT '', catalogo_pdf_url TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS products (
  id TEXT NOT NULL, tenant_id TEXT NOT NULL REFERENCES tenants(id),
  nombre TEXT NOT NULL, tipo TEXT DEFAULT '', parecido_a TEXT DEFAULT '', notas TEXT DEFAULT '',
  precio_frasco INTEGER NOT NULL, precio_decant INTEGER NOT NULL,
  stock_frasco INTEGER NOT NULL DEFAULT 0, stock_decant INTEGER NOT NULL DEFAULT 0,
  foto_url TEXT DEFAULT '', PRIMARY KEY (id, tenant_id)
);
CREATE TABLE IF NOT EXISTS orders (
  id SERIAL PRIMARY KEY, tenant_id TEXT NOT NULL REFERENCES tenants(id),
  cliente_wa TEXT NOT NULL, nombre TEXT NOT NULL, direccion TEXT NOT NULL, telefono TEXT NOT NULL,
  items JSONB NOT NULL, total INTEGER NOT NULL, pago TEXT DEFAULT '',
  estado TEXT NOT NULL DEFAULT 'pago_pendiente_verificacion',
  created_at TIMESTAMP DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_orders_tenant ON orders(tenant_id);
CREATE TABLE IF NOT EXISTS conversations (
  tenant_id TEXT NOT NULL REFERENCES tenants(id), cliente_wa TEXT NOT NULL,
  history JSONB NOT NULL DEFAULT '[]', escalada INTEGER DEFAULT 0,
  updated_at TIMESTAMP DEFAULT now(), PRIMARY KEY (tenant_id, cliente_wa)
);
CREATE TABLE IF NOT EXISTS processed_messages (
  message_id TEXT PRIMARY KEY, created_at TIMESTAMP DEFAULT now()
);
