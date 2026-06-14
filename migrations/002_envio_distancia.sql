-- F2: columnas para envío por distancia (geolocalización). Postgres/Neon.
-- Idempotente (IF NOT EXISTS). CORRER ANTES de desplegar el código de F2:
-- una vez que models.py tiene estas columnas, todo INSERT/UPDATE de conversations/orders
-- las referencia; si faltan en la BD, el ORM falla. Migrar primero, desplegar después.

ALTER TABLE conversations ADD COLUMN IF NOT EXISTS ultima_ubicacion JSONB;
ALTER TABLE orders        ADD COLUMN IF NOT EXISTS ubicacion        JSONB;
ALTER TABLE orders        ADD COLUMN IF NOT EXISTS distancia_km     DOUBLE PRECISION;
