"use client";
import { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { auth, setToken } from "@/lib/api";

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

const PUBLIC = ["/login", "/reset", "/forgot"];

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);
  const router = useRouter();
  const path = usePathname();

  useEffect(() => {
    const t = typeof window !== "undefined" ? sessionStorage.getItem("strouv_token") : null;
    if (t) {
      setToken(t);
      auth.me().then(setUser).catch(() => { sessionStorage.removeItem("strouv_token"); setToken(null); })
        .finally(() => setReady(true));
    } else setReady(true);
  }, []);

  useEffect(() => {
    if (!ready) return;
    const isPublic = PUBLIC.some((p) => path.startsWith(p));
    if (!user && !isPublic) router.replace("/login");
    if (user && isPublic) router.replace("/dashboard");
  }, [ready, user, path, router]);

  async function login(email, password) {
    const r = await auth.login(email, password);
    sessionStorage.setItem("strouv_token", r.token);
    setToken(r.token);
    setUser(r.user);
    router.replace("/dashboard");
  }
  function logout() {
    sessionStorage.removeItem("strouv_token");
    setToken(null); setUser(null);
    router.replace("/login");
  }

  return <Ctx.Provider value={{ user, ready, login, logout }}>{children}</Ctx.Provider>;
}
