"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { useAuth } from "@/components/AuthProvider";
import { Btn, inputCls } from "@/components/ui";

export default function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [pass, setPass] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setErr(""); setLoading(true);
    try { await login(email, pass); }
    catch { setErr("Correo o contraseña incorrectos."); setLoading(false); }
  }

  return (
    <div className="min-h-screen grid place-items-center px-4">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: [0.21, 0.5, 0.3, 1] }}
        className="w-full max-w-sm">
        <div className="flex items-center gap-2.5 mb-8 justify-center">
          <motion.span initial={{ scale: 0.6, rotate: -12 }} animate={{ scale: 1, rotate: 0 }} transition={{ type: "spring", stiffness: 200, delay: 0.1 }}
            className="h-9 w-9 rounded-xl bg-brand shadow-glow" />
          <span className="font-display text-2xl font-semibold tracking-tight">Strouv</span>
        </div>

        <div className="rounded-2xl border border-line bg-surface/80 backdrop-blur-sm p-7 shadow-glow">
          <h1 className="font-display text-xl font-semibold mb-1">Entra a tu panel</h1>
          <p className="text-sm text-muted mb-6">Gestiona tu asistente de ventas</p>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="text-sm text-strouv-light/90">Correo</label>
              <input type="email" required className={`${inputCls} mt-1.5`} value={email}
                onChange={(e) => setEmail(e.target.value)} placeholder="tu@correo.com" />
            </div>
            <div>
              <label className="text-sm text-strouv-light/90">Contraseña</label>
              <input type="password" required className={`${inputCls} mt-1.5`} value={pass}
                onChange={(e) => setPass(e.target.value)} placeholder="••••••••" />
            </div>
            {err && <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-sm text-red-400">{err}</motion.p>}
            <Btn type="submit" className="w-full justify-center" disabled={loading}>
              {loading ? "Entrando…" : "Entrar"}
            </Btn>
          </form>

          <div className="mt-5 text-center">
            <Link href="/forgot" className="text-sm text-muted hover:text-strouv-light transition">¿Olvidaste tu contraseña?</Link>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
