"use client";
import { useState } from "react";
import useSWR from "swr";
import { motion, AnimatePresence } from "framer-motion";
import { fetcher, api, auth } from "@/lib/api";
import { Page, Card, Btn, Field, inputCls } from "@/components/ui";
import { Plus, Store, UserPlus, X, Check } from "lucide-react";

export default function Negocios() {
  const { data: tenants, mutate } = useSWR("/tenants", fetcher);
  const [creandoTenant, setCreandoTenant] = useState(false);
  const [ownerFor, setOwnerFor] = useState(null);

  return (
    <Page title="Negocios" subtitle="Da de alta clientes nuevos y crea su acceso al panel."
      action={<Btn onClick={() => setCreandoTenant(true)}><Plus size={16} /> Nuevo negocio</Btn>}>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {(tenants || []).map((t, i) => (
          <Card key={t.id} delay={i * 0.05} className="p-5">
            <div className="flex items-start gap-3">
              <span className="h-10 w-10 rounded-xl bg-surface-2 grid place-items-center text-strouv-light"><Store size={18} /></span>
              <div className="min-w-0">
                <h3 className="font-display font-medium truncate">{t.nombre}</h3>
                <p className="text-xs text-muted truncate">{t.rubro}</p>
              </div>
            </div>
            <div className="flex gap-4 mt-4 text-xs text-muted">
              <span>{t.n_productos} productos</span>
              <span>{t.n_pedidos} pedidos</span>
              <span className="ml-auto text-strouv-light/80">{t.vertical}</span>
            </div>
            <Btn variant="ghost" className="w-full justify-center mt-4" onClick={() => setOwnerFor(t)}>
              <UserPlus size={15} /> Crear cuenta de dueño
            </Btn>
          </Card>
        ))}
        {tenants && tenants.length === 0 && (
          <Card className="p-10 text-center col-span-full text-muted">Aún no hay negocios. Crea el primero.</Card>
        )}
      </div>

      <AnimatePresence>
        {creandoTenant && <TenantModal onClose={() => setCreandoTenant(false)} onDone={() => { setCreandoTenant(false); mutate(); }} />}
        {ownerFor && <OwnerModal tenant={ownerFor} onClose={() => setOwnerFor(null)} />}
      </AnimatePresence>
    </Page>
  );
}

function Modal({ children, onClose }) {
  return (
    <motion.div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/70 backdrop-blur-sm"
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}>
      <motion.div onClick={(e) => e.stopPropagation()}
        initial={{ opacity: 0, scale: 0.96, y: 10 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.97 }}
        transition={{ type: "spring", stiffness: 320, damping: 30 }}
        className="w-full max-w-lg rounded-2xl border border-line bg-surface shadow-glow p-6">
        {children}
      </motion.div>
    </motion.div>
  );
}

function TenantModal({ onClose, onDone }) {
  const [f, setF] = useState({ nombre: "", rubro: "", owner_wa: "" });
  const [err, setErr] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function crear() {
    setErr("");
    try {
      await api.createTenant({
        nombre: f.nombre, rubro: f.rubro, vertical: "perfumeria", owner_wa: f.owner_wa,
        wa_phone_id: `pendiente_${Date.now()}`, wa_token: "pendiente",
        envio_config: { costo: 250, gratis_desde: 5000, delivery_gsd: 200 },
        pago_config: "Transferencia, tPago, efectivo contra entrega",
        cuenta_mensaje: "Configura los datos de pago en el panel.",
        descuento_config: { min_frascos: 2, monto: 200, o_envio_gratis: true },
      });
      onDone();
    } catch (e) { setErr(e.message); }
  }

  return (
    <Modal onClose={onClose}>
      <div className="flex items-center justify-between mb-5">
        <h2 className="font-display text-xl font-semibold">Nuevo negocio</h2>
        <button onClick={onClose} className="text-muted hover:text-white"><X size={20} /></button>
      </div>
      <div className="space-y-4">
        <Field label="Nombre del negocio"><input className={inputCls} value={f.nombre} onChange={set("nombre")} placeholder="Royal Oud" /></Field>
        <Field label="Rubro"><input className={inputCls} value={f.rubro} onChange={set("rubro")} placeholder="perfumes árabes y de diseñador" /></Field>
        <Field label="WhatsApp del dueño" hint="opcional ahora; lo completa luego"><input className={inputCls} value={f.owner_wa} onChange={set("owner_wa")} placeholder="1829XXXXXXX" /></Field>
        <p className="text-xs text-muted">El resto (envío, pago, descuentos, WhatsApp) se configura después con valores por defecto editables.</p>
        {err && <p className="text-sm text-red-400">{err}</p>}
      </div>
      <div className="flex justify-end gap-2 mt-6">
        <Btn variant="subtle" onClick={onClose}>Cancelar</Btn>
        <Btn onClick={crear} disabled={!f.nombre || !f.rubro}>Crear negocio</Btn>
      </div>
    </Modal>
  );
}

function OwnerModal({ tenant, onClose }) {
  const [f, setF] = useState({ email: "", password: "", nombre: "" });
  const [done, setDone] = useState(false);
  const [err, setErr] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function crear() {
    setErr("");
    try {
      await auth.createOwner({ ...f, tenant_id: tenant.id });
      setDone(true);
    } catch (e) { setErr(e.message); }
  }

  return (
    <Modal onClose={onClose}>
      <div className="flex items-center justify-between mb-5">
        <h2 className="font-display text-xl font-semibold">Cuenta de dueño · {tenant.nombre}</h2>
        <button onClick={onClose} className="text-muted hover:text-white"><X size={20} /></button>
      </div>
      {done ? (
        <div className="text-center py-4">
          <span className="inline-grid place-items-center h-12 w-12 rounded-full bg-ok/15 text-ok mb-3"><Check size={24} /></span>
          <p className="text-sm text-muted">Cuenta creada. Pásale al dueño su correo y contraseña para que entre a <span className="text-strouv-light">{tenant.nombre}</span>.</p>
          <Btn className="mt-5" onClick={onClose}>Listo</Btn>
        </div>
      ) : (
        <>
          <div className="space-y-4">
            <Field label="Nombre del dueño"><input className={inputCls} value={f.nombre} onChange={set("nombre")} placeholder="Juan Pérez" /></Field>
            <Field label="Correo (usuario de acceso)"><input type="email" className={inputCls} value={f.email} onChange={set("email")} placeholder="dueno@royaloud.com" /></Field>
            <Field label="Contraseña temporal" hint="mínimo 8 caracteres; el dueño puede cambiarla luego"><input className={inputCls} value={f.password} onChange={set("password")} placeholder="••••••••" /></Field>
            {err && <p className="text-sm text-red-400">{err}</p>}
          </div>
          <div className="flex justify-end gap-2 mt-6">
            <Btn variant="subtle" onClick={onClose}>Cancelar</Btn>
            <Btn onClick={crear} disabled={!f.email || f.password.length < 8}>Crear cuenta</Btn>
          </div>
        </>
      )}
    </Modal>
  );
}
