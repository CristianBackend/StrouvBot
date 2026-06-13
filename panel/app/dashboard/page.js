"use client";
import useSWR from "swr";
import { motion } from "framer-motion";
import { fetcher, rd } from "@/lib/api";
import { useScope } from "@/lib/useScope";
import { Page, Card, Estado } from "@/components/ui";
import { TrendingUp, MessageSquare, ShoppingBag, Wallet, Building2 } from "lucide-react";

function Stat({ icon: Icon, label, value, accent, delay }) {
  return (
    <Card delay={delay} className="p-5">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted">{label}</span>
        <Icon size={18} className={accent ? "text-strouv-light" : "text-muted"} />
      </div>
      <div className="font-display text-3xl font-semibold mt-3 tabular">{value}</div>
    </Card>
  );
}

export default function Dashboard() {
  const { user, isAdmin } = useScope();
  if (!user) return null;
  return isAdmin ? <AdminDash /> : <OwnerDash />;
}

function AdminDash() {
  const { data: o } = useSWR("/overview", fetcher);
  return (
    <Page title="Resumen" subtitle="Vista global de Strouv">
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <Stat icon={Building2} label="Negocios activos" value={o?.tenants ?? "—"} accent delay={0} />
        <Stat icon={ShoppingBag} label="Pedidos totales" value={o?.pedidos ?? "—"} delay={0.06} />
        <Stat icon={Wallet} label="Ingresos confirmados" value={o ? rd(o.ingresos_confirmados) : "—"} accent delay={0.12} />
      </div>
      <Card delay={0.2} className="p-6 mt-6">
        <p className="text-muted text-sm">Administra los negocios desde <a href="/negocios" className="text-strouv-light underline">Negocios</a>: crea uno nuevo, configúralo y crea su cuenta de dueño.</p>
      </Card>
    </Page>
  );
}

function OwnerDash() {
  const { data: m } = useSWR("/metrics", fetcher);
  const { data: orders } = useSWR("/orders", fetcher);
  const recientes = (orders || []).slice(0, 6);
  return (
    <Page title="Resumen" subtitle="Cómo va tu embudo de ventas">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Stat icon={MessageSquare} label="Conversaciones" value={m?.conversaciones ?? "—"} delay={0} />
        <Stat icon={ShoppingBag} label="Pedidos" value={m?.pedidos ?? "—"} accent delay={0.06} />
        <Stat icon={Wallet} label="Ingresos confirmados" value={m ? rd(m.ingresos_confirmados) : "—"} delay={0.12} />
        <Stat icon={TrendingUp} label="Conversión" value={m ? `${Math.round((m.conversion || 0) * 100)}%` : "—"} accent delay={0.18} />
      </div>
      <Card delay={0.24} className="overflow-hidden">
        <div className="px-5 py-4 border-b border-line flex items-center justify-between">
          <h2 className="font-display font-medium">Pedidos recientes</h2>
          <a href="/pedidos" className="text-xs text-strouv-light hover:underline">Ver todos</a>
        </div>
        {recientes.length === 0 ? (
          <div className="px-5 py-10 text-center text-muted text-sm">Cuando entren pedidos por WhatsApp, aparecerán aquí.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-muted text-xs">
              <tr className="border-b border-line">
                <th className="text-left font-medium px-5 py-2.5">Pedido</th>
                <th className="text-left font-medium px-5 py-2.5">Cliente</th>
                <th className="text-right font-medium px-5 py-2.5">Total</th>
                <th className="text-left font-medium px-5 py-2.5">Estado</th>
              </tr>
            </thead>
            <tbody>
              {recientes.map((o, i) => (
                <motion.tr key={o.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 + i * 0.04 }}
                  className="border-b border-line/50 last:border-0 hover:bg-surface-2/40">
                  <td className="px-5 py-3 font-display tabular">#{o.id}</td>
                  <td className="px-5 py-3">{o.nombre || o.cliente_wa}</td>
                  <td className="px-5 py-3 text-right tabular">{rd(o.total)}</td>
                  <td className="px-5 py-3"><Estado value={o.estado} /></td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </Page>
  );
}
