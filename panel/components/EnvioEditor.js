"use client";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Trash2, Truck, Store, MapPin } from "lucide-react";
import { Field, inputCls } from "./ui";

const TIPOS = {
  fijo: { label: "Tarifa fija", icon: Truck },
  zona: { label: "Zona", icon: MapPin },
  retiro: { label: "Retiro en tienda", icon: Store },
};

let _id = 0;
const nuevoId = () => `m_${Date.now()}_${_id++}`;

export default function EnvioEditor({ value, onChange }) {
  const cfg = value || { metodos: [], gratis_desde: 0, gratis_activo: false };
  const metodos = cfg.metodos || [];

  const setMetodos = (m) => onChange({ ...cfg, metodos: m });
  const updateMetodo = (i, patch) => setMetodos(metodos.map((m, k) => (k === i ? { ...m, ...patch } : m)));
  const addMetodo = (tipo) => setMetodos([...metodos, { id: nuevoId(), tipo, nombre: tipo === "retiro" ? "Retiro en tienda" : "", costo: 0 }]);
  const delMetodo = (i) => setMetodos(metodos.filter((_, k) => k !== i));

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <AnimatePresence initial={false}>
          {metodos.map((m, i) => {
            const Icon = (TIPOS[m.tipo] || TIPOS.fijo).icon;
            return (
              <motion.div key={m.id} layout
                initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
                className="flex items-center gap-2 rounded-lg bg-ink/50 border border-line p-2.5">
                <span className="h-8 w-8 shrink-0 grid place-items-center rounded-lg bg-surface-2 text-strouv-light"><Icon size={15} /></span>
                <input className={`${inputCls} flex-1`} placeholder={m.tipo === "zona" ? "Nombre de la zona (ej. Santiago)" : "Nombre del método"}
                  value={m.nombre} onChange={(e) => updateMetodo(i, { nombre: e.target.value })} />
                {m.tipo !== "retiro" && (
                  <div className="flex items-center gap-1 shrink-0">
                    <span className="text-xs text-muted">RD$</span>
                    <input type="number" className={`${inputCls} w-24 tabular`} value={m.costo}
                      onChange={(e) => updateMetodo(i, { costo: +e.target.value })} />
                  </div>
                )}
                <button type="button" onClick={() => delMetodo(i)} className="p-2 text-muted hover:text-red-400 shrink-0"><Trash2 size={15} /></button>
              </motion.div>
            );
          })}
        </AnimatePresence>
        {metodos.length === 0 && <p className="text-xs text-muted py-2">Agrega al menos un método de envío.</p>}
      </div>

      <div className="flex flex-wrap gap-2">
        {Object.entries(TIPOS).map(([tipo, { label, icon: Icon }]) => (
          <button key={tipo} type="button" onClick={() => addMetodo(tipo)}
            className="inline-flex items-center gap-1.5 text-xs rounded-lg px-3 py-1.5 bg-surface-2 text-muted hover:text-white ring-1 ring-line transition">
            <Plus size={13} /> {label}
          </button>
        ))}
      </div>

      <div className="rounded-lg bg-ink/40 border border-line p-3 flex items-center gap-3">
        <button type="button" onClick={() => onChange({ ...cfg, gratis_activo: !cfg.gratis_activo })}
          className={`relative h-6 w-11 rounded-full transition ${cfg.gratis_activo ? "bg-brand" : "bg-line"}`}>
          <motion.span layout className="absolute top-0.5 h-5 w-5 rounded-full bg-white"
            animate={{ left: cfg.gratis_activo ? 22 : 2 }} transition={{ type: "spring", stiffness: 500, damping: 35 }} />
        </button>
        <div className="flex-1">
          <div className="text-sm">Envío gratis por monto</div>
          <div className="text-xs text-muted">Si el pedido supera cierto monto, el envío es gratis</div>
        </div>
        {cfg.gratis_activo && (
          <div className="flex items-center gap-1">
            <span className="text-xs text-muted">desde RD$</span>
            <input type="number" className={`${inputCls} w-24 tabular`} value={cfg.gratis_desde}
              onChange={(e) => onChange({ ...cfg, gratis_desde: +e.target.value })} />
          </div>
        )}
      </div>
    </div>
  );
}
