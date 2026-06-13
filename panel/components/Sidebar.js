"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { LayoutDashboard, Package, ShoppingBag, Settings2, Building2, LogOut } from "lucide-react";
import { useAuth } from "./AuthProvider";

const navOwner = [
  { href: "/dashboard", label: "Resumen", icon: LayoutDashboard },
  { href: "/catalogo", label: "Catálogo", icon: Package },
  { href: "/pedidos", label: "Pedidos", icon: ShoppingBag },
  { href: "/config", label: "Configuración", icon: Settings2 },
];
const navAdmin = [
  { href: "/dashboard", label: "Resumen", icon: LayoutDashboard },
  { href: "/negocios", label: "Negocios", icon: Building2 },
];

export default function Sidebar() {
  const path = usePathname();
  const { user, logout } = useAuth();
  const nav = user?.rol === "super_admin" ? navAdmin : navOwner;

  return (
    <aside className="w-[230px] shrink-0 min-h-screen border-r border-line bg-ink/60 backdrop-blur-sm px-4 py-6 sticky top-0 hidden md:flex md:flex-col">
      <Link href="/dashboard" className="flex items-center gap-2 px-2 mb-9">
        <span className="h-7 w-7 rounded-lg bg-brand shadow-glow" />
        <span className="font-display text-xl font-semibold tracking-tight">Strouv</span>
        {user?.rol === "super_admin" && <span className="text-[10px] text-strouv-light bg-strouv/15 px-1.5 py-0.5 rounded ml-1">admin</span>}
      </Link>

      <nav className="flex flex-col gap-1">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = path === href || (href !== "/dashboard" && path.startsWith(href));
          return (
            <Link key={href} href={href}
              className="relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors hover:bg-surface">
              {active && <motion.span layoutId="nav-active" className="absolute inset-0 rounded-lg bg-surface-2 ring-1 ring-line" transition={{ type: "spring", stiffness: 380, damping: 32 }} />}
              {active && <span className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-full bg-brand" />}
              <Icon size={18} className={`relative z-10 ${active ? "text-strouv-light" : "text-muted"}`} />
              <span className={`relative z-10 ${active ? "text-white" : "text-muted"}`}>{label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto pt-6">
        <div className="px-2 mb-3 text-xs text-muted truncate">{user?.email}</div>
        <button onClick={logout} className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-muted hover:text-white hover:bg-surface w-full transition">
          <LogOut size={18} /> Salir
        </button>
      </div>
    </aside>
  );
}
