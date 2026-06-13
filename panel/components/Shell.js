"use client";
import { usePathname } from "next/navigation";
import { useAuth } from "./AuthProvider";
import Sidebar from "./Sidebar";

const PUBLIC = ["/login", "/reset", "/forgot"];

export default function Shell({ children }) {
  const path = usePathname();
  const { ready, user } = useAuth();
  const isPublic = PUBLIC.some((p) => path.startsWith(p));

  if (!ready) return <div className="min-h-screen grid place-items-center text-muted">Cargando…</div>;
  if (isPublic) return <main className="min-h-screen">{children}</main>;
  if (!user) return null; // el provider redirige a /login

  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1 min-h-screen">{children}</main>
    </div>
  );
}
