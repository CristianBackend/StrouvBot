"use client";
import { useState, useEffect } from "react";
import useSWR from "swr";
import { motion, AnimatePresence } from "framer-motion";
import { fetcher, api } from "@/lib/api";
import { Page, Card, Btn, Field, inputCls } from "@/components/ui";
import EnvioEditor from "@/components/EnvioEditor";
import PromoEditor from "@/components/PromoEditor";
import { Check } from "lucide-react";

const def = {
  nombre: "", rubro: "", owner_wa: "", wa_phone_id: "", wa_token: "",
  pago_config: "", cuenta_mensaje: "", info_extra: "", catalogo_pdf_url: "",
  envio_config: { metodos: [{ id: "fijo", tipo: "fijo", nombre: "Envío estándar", costo: 250 }], gratis_desde: 5000, gratis_activo: true },
  descuento_config: { promos: [] },
};

// Normaliza configs viejas a las nuevas estructuras al cargar (por si el tenant trae formato viejo).
function normEnvio(e) {
  if (!e) return def.envio_config;
  if (e.metodos) return e;
  const metodos = [{ id: "fijo", tipo: "fijo", nombre: "Envío estándar", costo: e.costo || 0 }];
  if (e.delivery_gsd != null) metodos.push({ id: "gsd", tipo: "zona", nombre: "Delivery GSD", costo: e.delivery_gsd });
  return { metodos, gratis_desde: e.gratis_desde || 0, gratis_activo: (e.gratis_desde || 0) > 0 };
}
function normPromos(d) {
  if (!d) return { promos: [] };
  if (d.promos) return d;
  if (d.min_frascos) return { promos: [{ id: "p_old", tipo: "cantidad_frascos", activo: true, min_frascos: d.min_frascos, monto: d.monto || 0, envio_gratis: !!d.o_envio_gratis }] };
  return { promos: [] };
}

export default function Config() {
  const { data: tenant, mutate } = useSWR("/tenant", fetcher);
  const [f, setF] = useState(def);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (tenant) setF({ ...def, ...tenant, envio_config: normEnvio(tenant.envio_config), descuento_config: normPromos(tenant.descuento_config) });
  }, [tenant]);

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function save() {
    const { nombre, rubro, owner_wa, wa_phone_id, wa_token, envio_config,
            pago_config, cuenta_mensaje, descuento_config, info_extra, catalogo_pdf_url } = f;
    await api.updateTenant({ nombre, rubro, owner_wa, wa_phone_id, wa_token, envio_config,
      pago_config, cuenta_mensaje, descuento_config, info_extra, catalogo_pdf_url });
    setSaved(true); mutate();
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <Page title="Configuración" subtitle="Los datos que tu bot usa como única fuente de verdad."
      action={<Btn onClick={save}><AnimatePresence mode="wait">{saved ? (
        <motion.span key="ok" initial={{ scale: 0 }} animate={{ scale: 1 }} className="flex items-center gap-2"><Check size={16} /> Guardado</motion.span>
      ) : <motion.span key="s">Guardar cambios</motion.span>}</AnimatePresence></Btn>}>

      <div className="grid lg:grid-cols-2 gap-5">
        <Card delay={0} className="p-6 space-y-4">
          <h2 className="font-display font-medium text-strouv-light">Negocio</h2>
          <Field label="Nombre"><input className={inputCls} value={f.nombre} onChange={set("nombre")} placeholder="Royal Oud" /></Field>
          <Field label="Rubro"><input className={inputCls} value={f.rubro} onChange={set("rubro")} placeholder="perfumes árabes y de diseñador" /></Field>
          <Field label="Info extra" hint="horario, ubicación, garantías"><input className={inputCls} value={f.info_extra} onChange={set("info_extra")} /></Field>
        </Card>

        <Card delay={0.06} className="p-6 space-y-4">
          <h2 className="font-display font-medium text-strouv-light">WhatsApp</h2>
          <Field label="Tu WhatsApp (dueño)" hint="recibes pedidos y respondes PAGADO / DESPACHADO"><input className={inputCls} value={f.owner_wa} onChange={set("owner_wa")} placeholder="1829XXXXXXX" /></Field>
          <Field label="Phone Number ID" hint="de Meta Cloud API"><input className={inputCls} value={f.wa_phone_id} onChange={set("wa_phone_id")} /></Field>
          <Field label="Token de WhatsApp"><input type="password" className={inputCls} value={f.wa_token} onChange={set("wa_token")} placeholder="••••••••" /></Field>
        </Card>

        <Card delay={0.12} className="p-6 space-y-4 lg:col-span-2">
          <div>
            <h2 className="font-display font-medium text-strouv-light">Métodos de envío</h2>
            <p className="text-xs text-muted mt-0.5">Define tus zonas y precios según tu ubicación. El bot ubica al cliente y confirma el costo antes de cobrar.</p>
          </div>
          <EnvioEditor value={f.envio_config} onChange={(v) => setF({ ...f, envio_config: v })} />
        </Card>

        <Card delay={0.18} className="p-6 space-y-4 lg:col-span-2">
          <div>
            <h2 className="font-display font-medium text-strouv-light">Promociones</h2>
            <p className="text-xs text-muted mt-0.5">Agrega las que quieras y actívalas o desactívalas. El bot aplica siempre la más favorable al cliente.</p>
          </div>
          <PromoEditor value={f.descuento_config} onChange={(v) => setF({ ...f, descuento_config: v })} />
        </Card>

        <Card delay={0.24} className="p-6 space-y-4 lg:col-span-2">
          <h2 className="font-display font-medium text-strouv-light">Pago</h2>
          <Field label="Métodos de pago"><input className={inputCls} value={f.pago_config} onChange={set("pago_config")} placeholder="Transferencia, tPago, efectivo contra entrega" /></Field>
          <Field label="Mensaje de la cuenta" hint="el bot lo envía TAL CUAL — un dígito mal aquí es un pago perdido">
            <textarea rows={4} className={`${inputCls} resize-none`} value={f.cuenta_mensaje} onChange={set("cuenta_mensaje")}
              placeholder={"Banreservas — Ahorros 960-123456-7\nA nombre de…"} />
          </Field>
        </Card>
      </div>
    </Page>
  );
}
