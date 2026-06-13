"use client";
import { useState } from "react";
import useSWR from "swr";
import { motion, AnimatePresence } from "framer-motion";
import { fetcher, api, rd } from "@/lib/api";
import { Page, Card, Btn, Field, inputCls } from "@/components/ui";
import { Plus, Pencil, Trash2, X } from "lucide-react";
import ImageUpload from "@/components/ImageUpload";

const empty = { id: "", nombre: "", tipo: "", parecido_a: "", notas: "",
  precio_frasco: 0, precio_decant: 0, stock_frasco: 0, stock_decant: 0, foto_url: "" };

export default function Catalogo() {
  const { data: products, mutate } = useSWR("/products", fetcher);
  const [editing, setEditing] = useState(null); // objeto producto o null

  async function save(form) {
    await api.saveProduct({
      ...form,
      precio_frasco: +form.precio_frasco, precio_decant: +form.precio_decant,
      stock_frasco: +form.stock_frasco, stock_decant: +form.stock_decant,
    });
    setEditing(null); mutate();
  }
  async function remove(pid) {
    if (!confirm("¿Eliminar este producto del catálogo?")) return;
    await api.deleteProduct(pid); mutate();
  }

  return (
    <Page title="Catálogo" subtitle="Lo único que el bot puede vender. Si no está aquí, no existe."
      action={<Btn onClick={() => setEditing({ ...empty })}><Plus size={16} /> Agregar producto</Btn>}>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {(products || []).map((p, i) => (
          <Card key={p.id} delay={i * 0.05} className="p-5 group">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-display font-medium text-lg leading-tight">{p.nombre}</h3>
                <p className="text-xs text-muted mt-1">{p.tipo}{p.parecido_a && ` · como ${p.parecido_a}`}</p>
              </div>
              <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition">
                <button onClick={() => setEditing(p)} className="p-1.5 rounded-md hover:bg-surface-2 text-muted hover:text-strouv-light"><Pencil size={15} /></button>
                <button onClick={() => remove(p.id)} className="p-1.5 rounded-md hover:bg-surface-2 text-muted hover:text-red-400"><Trash2 size={15} /></button>
              </div>
            </div>
            {p.notas && <p className="text-sm text-muted/90 mt-3 line-clamp-2">{p.notas}</p>}
            <div className="grid grid-cols-2 gap-2 mt-4">
              <Slot label="Frasco" precio={p.precio_frasco} stock={p.stock_frasco} />
              <Slot label="Decant" precio={p.precio_decant} stock={p.stock_decant} />
            </div>
          </Card>
        ))}
        {products && products.length === 0 && (
          <Card className="p-10 text-center col-span-full text-muted">
            Tu catálogo está vacío. Agrega tu primer perfume.
          </Card>
        )}
      </div>

      <AnimatePresence>
        {editing && <Editor product={editing} onSave={save} onClose={() => setEditing(null)} />}
      </AnimatePresence>
    </Page>
  );
}

function Slot({ label, precio, stock }) {
  const agotado = stock <= 0;
  return (
    <div className="rounded-lg bg-ink/50 border border-line px-3 py-2">
      <div className="text-[11px] text-muted">{label}</div>
      <div className="font-display tabular text-sm mt-0.5">{rd(precio)}</div>
      <div className={`text-[11px] mt-0.5 ${agotado ? "text-red-400" : "text-muted"}`}>
        {agotado ? "Agotado" : `${stock} en stock`}
      </div>
    </div>
  );
}

function Editor({ product, onSave, onClose }) {
  const [f, setF] = useState(product);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const isNew = !product.nombre;
  return (
    <motion.div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/70 backdrop-blur-sm"
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}>
      <motion.div onClick={(e) => e.stopPropagation()}
        initial={{ opacity: 0, scale: 0.96, y: 10 }} animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.97 }} transition={{ type: "spring", stiffness: 320, damping: 30 }}
        className="w-full max-w-lg rounded-2xl border border-line bg-surface shadow-glow p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-display text-xl font-semibold">{isNew ? "Nuevo producto" : f.nombre}</h2>
          <button onClick={onClose} className="text-muted hover:text-white"><X size={20} /></button>
        </div>
        <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-1">
          <div className="grid grid-cols-2 gap-3">
            <Field label="ID (sin espacios)" hint="ej. khamrah — el bot lo usa internamente">
              <input className={inputCls} value={f.id} onChange={set("id")} disabled={!isNew} placeholder="khamrah" />
            </Field>
            <Field label="Nombre"><input className={inputCls} value={f.nombre} onChange={set("nombre")} placeholder="Lattafa Khamrah" /></Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Tipo"><input className={inputCls} value={f.tipo} onChange={set("tipo")} placeholder="Árabe" /></Field>
            <Field label="Parecido a"><input className={inputCls} value={f.parecido_a} onChange={set("parecido_a")} placeholder="Angels' Share" /></Field>
          </div>
          <Field label="Notas"><input className={inputCls} value={f.notas} onChange={set("notas")} placeholder="dulce, canela, dátiles" /></Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Precio frasco"><input type="number" className={`${inputCls} tabular`} value={f.precio_frasco} onChange={set("precio_frasco")} /></Field>
            <Field label="Precio decant"><input type="number" className={`${inputCls} tabular`} value={f.precio_decant} onChange={set("precio_decant")} /></Field>
            <Field label="Stock frasco"><input type="number" className={`${inputCls} tabular`} value={f.stock_frasco} onChange={set("stock_frasco")} /></Field>
            <Field label="Stock decant"><input type="number" className={`${inputCls} tabular`} value={f.stock_decant} onChange={set("stock_decant")} /></Field>
          </div>
          <Field label="Foto del producto" hint="el bot la envía cuando recomienda el perfume">
            <ImageUpload value={f.foto_url} onUploaded={(url) => setF({ ...f, foto_url: url })} />
          </Field>
        </div>
        <div className="flex justify-end gap-2 mt-6">
          <Btn variant="subtle" onClick={onClose}>Cancelar</Btn>
          <Btn onClick={() => onSave(f)} disabled={!f.id || !f.nombre}>Guardar producto</Btn>
        </div>
      </motion.div>
    </motion.div>
  );
}
