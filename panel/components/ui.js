"use client";
import { motion } from "framer-motion";

export function Page({ title, subtitle, action, children }) {
  return (
    <div className="px-6 md:px-10 py-8 max-w-[1200px] mx-auto">
      <header className="flex items-start justify-between gap-4 mb-8">
        <div>
          <h1 className="font-display text-2xl md:text-3xl font-semibold tracking-tight">{title}</h1>
          {subtitle && <p className="text-muted text-sm mt-1.5">{subtitle}</p>}
        </div>
        {action}
      </header>
      {children}
    </div>
  );
}

export function Card({ children, className = "", delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: [0.21, 0.5, 0.3, 1] }}
      className={`rounded-2xl border border-line bg-surface/80 backdrop-blur-sm ${className}`}>
      {children}
    </motion.div>
  );
}

export function Btn({ children, variant = "primary", className = "", ...p }) {
  const styles = {
    primary: "bg-brand text-white shadow-glow hover:brightness-110",
    ghost: "bg-surface-2 text-strouv-light ring-1 ring-line hover:bg-line/40",
    subtle: "text-muted hover:text-white hover:bg-surface",
  };
  return (
    <button {...p}
      className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all active:scale-[0.97] ${styles[variant]} ${className}`}>
      {children}
    </button>
  );
}

export function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="text-sm text-strouv-light/90">{label}</span>
      {hint && <span className="block text-xs text-muted mt-0.5 mb-1.5">{hint}</span>}
      <div className={hint ? "" : "mt-1.5"}>{children}</div>
    </label>
  );
}

export const inputCls =
  "w-full rounded-lg bg-ink/70 border border-line px-3 py-2 text-sm text-white " +
  "placeholder:text-muted/60 outline-none focus:border-strouv focus:ring-2 focus:ring-strouv/30 transition";

const estadoMap = {
  pago_pendiente_verificacion: { t: "Pendiente", c: "text-warn bg-warn/10 ring-warn/20" },
  pagado: { t: "Pagado", c: "text-ok bg-ok/10 ring-ok/20" },
  despachado: { t: "Despachado", c: "text-strouv-light bg-strouv/10 ring-strouv/20" },
  cancelado: { t: "Cancelado", c: "text-muted bg-line/30 ring-line" },
};
export function Estado({ value }) {
  const e = estadoMap[value] || estadoMap.cancelado;
  return <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ${e.c}`}>{e.t}</span>;
}
