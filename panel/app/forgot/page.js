"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { auth } from "@/lib/api";
import { Btn, inputCls } from "@/components/ui";

export default function Forgot() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  async function submit(e) { e.preventDefault(); await auth.forgot(email).catch(() => {}); setSent(true); }

  return (
    <div className="min-h-screen grid place-items-center px-4">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-sm">
        <div className="rounded-2xl border border-line bg-surface/80 backdrop-blur-sm p-7 shadow-glow">
          <h1 className="font-display text-xl font-semibold mb-1">Recupera tu acceso</h1>
          {sent ? (
            <p className="text-sm text-muted mt-3">Si el correo está registrado, te enviamos un enlace para crear una contraseña nueva. Revisa tu bandeja.</p>
          ) : (
            <>
              <p className="text-sm text-muted mb-6">Te enviaremos un enlace a tu correo.</p>
              <form onSubmit={submit} className="space-y-4">
                <input type="email" required className={inputCls} value={email}
                  onChange={(e) => setEmail(e.target.value)} placeholder="tu@correo.com" />
                <Btn type="submit" className="w-full justify-center">Enviar enlace</Btn>
              </form>
            </>
          )}
          <div className="mt-5 text-center">
            <Link href="/login" className="text-sm text-muted hover:text-strouv-light transition">Volver a entrar</Link>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
