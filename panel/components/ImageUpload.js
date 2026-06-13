"use client";
import { useState, useRef } from "react";
import { motion } from "framer-motion";
import { Upload, X, Loader2, ImageIcon } from "lucide-react";

// Sube una imagen al backend y devuelve la URL pública vía onUploaded(url).
export default function ImageUpload({ value, onUploaded }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const inputRef = useRef(null);

  async function handleFile(file) {
    if (!file) return;
    setErr(""); setBusy(true);
    try {
      const token = sessionStorage.getItem("strouv_token");
      const fd = new FormData();
      fd.append("file", file);
      const r = await fetch("/api/admin/upload", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        throw new Error(d.detail || "No se pudo subir");
      }
      const { url } = await r.json();
      onUploaded(url);
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  }

  return (
    <div>
      <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0])} />
      {value ? (
        <div className="relative inline-block">
          <img src={value} alt="" className="h-28 w-28 object-cover rounded-xl border border-line" />
          <button type="button" onClick={() => onUploaded("")}
            className="absolute -top-2 -right-2 h-6 w-6 grid place-items-center rounded-full bg-ink border border-line text-muted hover:text-red-400">
            <X size={14} />
          </button>
          <button type="button" onClick={() => inputRef.current?.click()}
            className="absolute bottom-1 right-1 text-[11px] bg-ink/80 backdrop-blur px-2 py-0.5 rounded-md text-strouv-light border border-line">
            Cambiar
          </button>
        </div>
      ) : (
        <motion.button type="button" whileTap={{ scale: 0.98 }} onClick={() => inputRef.current?.click()}
          disabled={busy}
          className="h-28 w-full rounded-xl border border-dashed border-line bg-ink/40 grid place-items-center text-muted hover:border-strouv hover:text-strouv-light transition">
          {busy ? <Loader2 size={22} className="animate-spin" /> : (
            <span className="flex flex-col items-center gap-1.5 text-sm">
              <Upload size={20} /> Subir foto desde tu dispositivo
            </span>
          )}
        </motion.button>
      )}
      {err && <p className="text-xs text-red-400 mt-1.5">{err}</p>}
    </div>
  );
}
