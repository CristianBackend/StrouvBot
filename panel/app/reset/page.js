"use client";
import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import Link from "next/link";
import { auth } from "@/lib/api";
import { Btn, inputCls } from "@/components/ui";

function ResetForm() {
  const token = useSearchParams().get("token") || "";
  const [pass, setPass] = useState("");
  const [done, setDone] = useState(false);
  const [err, setErr] = useState("");
  async function submit(e) {
    e.preventDefault(); setErr("");
    try { await auth.reset(token, pass); setDone(true); }
    catch (e) { setErr("El enlace es inválido o expiró. Pide uno nuevo."); }
  }
  return (
    <div className="rounded-2xl border border-line bg-surface/80 backdrop-blur-sm p-7 shadow-glow">
      <h1 className="font-display text-xl font-semibold mb-1">Nueva contraseña</h1>
      {done ? (
        <>
          <p className="text-sm text-muted mt-3 mb-5">Listo. Ya puedes entrar con tu nueva contraseña.</p>
          <Link href="/login"><Btn className="w-full justify-center">Ir a entrar</Btn></Link>
        </>
      ) : (
        <>
          <p className="text-sm text-muted mb-6">Mínimo 8 caracteres.</p>
          <form onSubmit={submit} className="space-y-4">
            <input type="password" required minLength={8} className={inputCls} value={pass}
              onChange={(e) => setPass(e.target.value)} placeholder="••••••••" />
            {err && <p className="text-sm text-red-400">{err}</p>}
            <Btn type="submit" className="w-full justify-center">Guardar contraseña</Btn>
          </form>
        </>
      )}
    </div>
  );
}

export default function Reset() {
  return (
    <div className="min-h-screen grid place-items-center px-4">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-sm">
        <Suspense><ResetForm /></Suspense>
      </motion.div>
    </div>
  );
}
