"use client";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Trash2, Tag, Percent, Package } from "lucide-react";
import { inputCls } from "./ui";

const TIPOS = {
  cantidad_frascos: { label: "Por cantidad de frascos", icon: Package },
  monto_minimo: { label: "Por monto mínimo", icon: Tag },
  porcentaje: { label: "Descuento %", icon: Percent },
};

let _id = 0;
const nuevoId = () => `p_${Date.now()}_${_id++}`;

export default function PromoEditor({ value, onChange }) {
  const promos = (value && value.promos) || [];
  const setPromos = (p) => onChange({ promos: p });
  const update = (i, patch) => setPromos(promos.map((p, k) => (k === i ? { ...p, ...patch } : p)));
  const add = (tipo) => {
    const base = { id: nuevoId(), tipo, activo: true };
    if (tipo === "cantidad_frascos") Object.assign(base, { min_frascos: 2, monto: 200, envio_gratis: false });
    if (tipo === "monto_minimo") Object.assign(base, { minimo: 5000, porcentaje: 0, monto: 0, envio_gratis: true });
    if (tipo === "porcentaje") Object.assign(base, { porcentaje: 10 });
    setPromos([...promos, base]);
  };
  const del = (i) => setPromos(promos.filter((_, k) => k !== i));

  return (
    <div className="space-y-3">
      <AnimatePresence initial={false}>
        {promos.map((p, i) => {
          const Icon = (TIPOS[p.tipo] || TIPOS.porcentaje).icon;
          return (
            <motion.div key={p.id} layout
              initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, height: 0 }}
              className="rounded-xl bg-ink/50 border border-line p-3.5">
              <div className="flex items-center gap-2 mb-3">
                <span className="h-8 w-8 grid place-items-center rounded-lg bg-surface-2 text-strouv-light"><Icon size={15} /></span>
                <span className="text-sm font-medium flex-1">{TIPOS[p.tipo]?.label}</span>
                <button type="button" onClick={() => update(i, { activo: !p.activo })}
                  className={`relative h-5 w-9 rounded-full transition ${p.activo ? "bg-brand" : "bg-line"}`}>
                  <motion.span layout className="absolute top-0.5 h-4 w-4 rounded-full bg-white"
                    animate={{ left: p.activo ? 18 : 2 }} transition={{ type: "spring", stiffness: 500, damping: 35 }} />
                </button>
                <button type="button" onClick={() => del(i)} className="p-1.5 text-muted hover:text-red-400"><Trash2 size={14} /></button>
              </div>

              <div className="grid grid-cols-2 gap-2 text-sm">
                {p.tipo === "cantidad_frascos" && (<>
                  <L label="Desde (frascos)"><input type="number" className={`${inputCls} tabular`} value={p.min_frascos} onChange={(e) => update(i, { min_frascos: +e.target.value })} /></L>
                  <L label="Descuento RD$"><input type="number" className={`${inputCls} tabular`} value={p.monto} onChange={(e) => update(i, { monto: +e.target.value })} /></L>
                  <Check label="…o envío gratis" checked={p.envio_gratis} onClick={() => update(i, { envio_gratis: !p.envio_gratis })} />
                </>)}
                {p.tipo === "monto_minimo" && (<>
                  <L label="Monto mínimo RD$"><input type="number" className={`${inputCls} tabular`} value={p.minimo} onChange={(e) => update(i, { minimo: +e.target.value })} /></L>
                  <L label="Descuento %"><input type="number" className={`${inputCls} tabular`} value={p.porcentaje} onChange={(e) => update(i, { porcentaje: +e.target.value })} /></L>
                  <L label="…o monto fijo RD$"><input type="number" className={`${inputCls} tabular`} value={p.monto} onChange={(e) => update(i, { monto: +e.target.value })} /></L>
                  <Check label="…o envío gratis" checked={p.envio_gratis} onClick={() => update(i, { envio_gratis: !p.envio_gratis })} />
                </>)}
                {p.tipo === "porcentaje" && (
                  <L label="Descuento % sobre todo"><input type="number" className={`${inputCls} tabular`} value={p.porcentaje} onChange={(e) => update(i, { porcentaje: +e.target.value })} /></L>
                )}
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
      {promos.length === 0 && <p className="text-xs text-muted">Sin promociones. Precios fijos.</p>}

      <div className="flex flex-wrap gap-2">
        {Object.entries(TIPOS).map(([tipo, { label, icon: Icon }]) => (
          <button key={tipo} type="button" onClick={() => add(tipo)}
            className="inline-flex items-center gap-1.5 text-xs rounded-lg px-3 py-1.5 bg-surface-2 text-muted hover:text-white ring-1 ring-line transition">
            <Plus size={13} /> {label}
          </button>
        ))}
      </div>
    </div>
  );
}

function L({ label, children }) {
  return <label className="block"><span className="text-xs text-muted">{label}</span><div className="mt-1">{children}</div></label>;
}
function Check({ label, checked, onClick }) {
  return (
    <button type="button" onClick={onClick} className="flex items-center gap-2 text-xs text-muted self-end pb-2">
      <span className={`h-4 w-4 rounded border grid place-items-center ${checked ? "bg-brand border-strouv" : "border-line"}`}>
        {checked && <span className="text-white text-[10px]">✓</span>}
      </span>
      {label}
    </button>
  );
}
