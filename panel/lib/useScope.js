"use client";
import { useAuth } from "@/components/AuthProvider";
// El owner opera sobre su propio tenant (sin query). El super-admin elige uno;
// para v1 el dashboard del super-admin usa /overview, y la gestión por-tenant
// se hace desde /negocios pasando ?tenant=. Este hook centraliza ese "scope".
export function useScope() {
  const { user } = useAuth();
  const isAdmin = user?.rol === "super_admin";
  return { user, isAdmin };
}
