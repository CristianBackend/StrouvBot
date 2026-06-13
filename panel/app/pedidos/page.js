"use client";
import { useState } from "react";
import useSWR from "swr";
import { motion } from "framer-motion";
import { fetcher, api, rd } from "@/lib/api";
import { Page, Card, Estado, Btn } from "@/components/ui";
import { Check, Truck, X } from "lucide-react";

const filtros = [
  { k: "todos", t: "Todos" },
  { k: "pago_pendiente_verificacion", t: "Pendientes" },
  { k: "pagado", t: "Pagados" },
  { k: "despachado", t: "Despachados" },
];

export default function Pedidos() {
  const { data: orders, mutate } = useSWR("/orders", fetcher);
  const [filtro, setFiltro] = useState("todos");

  async function mover(o, estado) {
    await api.setOrderEstado(o.id, estado); mutate();
  }
  const list = (orders || []).filter((o) => filtro === "todos" || o.estado === filtro);

  return (
    <Page title="Pedidos" subtitle="Verifica el comprobante y marca el estado. El bot nunca confirma un pago solo.">
      <div className="flex gap-1.5 mb-5">
        {filtros.map((f) => (
          <button key={f.k} onClick={() => setFiltro(f.k)}
            className={`relative px-3.5 py-1.5 rounded-lg text-sm transition ${filtro === f.k ? "text-white" : "text-muted hover:text-white"}`}>
            {filtro === f.k && <motion.span layoutId="filtro" className="absolute inset-0 rounded-lg bg-surface-2 ring-1 ring-line" />}
            <span className="relative z-10">{f.t}</span>
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {list.map((o, i) => (
          <Card key={o.id} delay={i * 0.03} className="p-4">
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-4">
                <span className="font-display tabular text-muted">#{o.id}</span>
                <div>
                  <div className="font-medium">{o.nombre || o.cliente_wa}</div>
                  <div className="text-xs text-muted">{o.telefono} · {o.direccion}</div>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <span className="font-display tabular text-lg">{rd(o.total)}</span>
                <Estado value={o.estado} />
              </div>
            </div>
            <div className="flex items-center gap-3 mt-3 pt-3 border-t border-line/60 flex-wrap">
              <div className="text-xs text-muted flex-1 min-w-[180px]">
                {(o.items || []).map((it, k) => (
                  <span key={k} className="mr-2">{it.cantidad}× {it.producto_id} ({it.presentacion})</span>
                ))}
              </div>
              <div className="flex gap-2">
                {o.estado === "pago_pendiente_verificacion" && (
                  <Btn variant="ghost" onClick={() => mover(o, "pagado")}><Check size={15} /> Marcar pagado</Btn>
                )}
                {o.estado === "pagado" && (
                  <Btn variant="ghost" onClick={() => mover(o, "despachado")}><Truck size={15} /> Despachar</Btn>
                )}
                {o.estado !== "cancelado" && o.estado !== "despachado" && (
                  <Btn variant="subtle" onClick={() => mover(o, "cancelado")}><X size={15} /> Cancelar</Btn>
                )}
              </div>
            </div>
          </Card>
        ))}
        {orders && list.length === 0 && (
          <Card className="p-12 text-center text-muted">No hay pedidos en esta vista.</Card>
        )}
      </div>
    </Page>
  );
}
