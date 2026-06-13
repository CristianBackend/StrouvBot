// Cliente del backend. Inyecta el token JWT en cada llamada y lo lee de memoria
// (lo setea el AuthProvider). Las rutas pasan por el rewrite /api -> FastAPI.
let TOKEN = null;
export const setToken = (t) => { TOKEN = t; };

async function j(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  if (TOKEN) headers.Authorization = `Bearer ${TOKEN}`;
  const r = await fetch(`/api${path}`, { ...opts, headers });
  if (r.status === 401) { throw new Error("UNAUTHORIZED"); }
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    throw new Error(d.detail || `Error ${r.status}`);
  }
  return r.json();
}

// SWR fetcher (las rutas admin van con prefijo /admin)
export const fetcher = (path) => j(`/admin${path}`);

export const auth = {
  login: (email, password) => j("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => j("/auth/me"),
  forgot: (email) => j("/auth/forgot", { method: "POST", body: JSON.stringify({ email }) }),
  reset: (token, password) => j("/auth/reset", { method: "POST", body: JSON.stringify({ token, password }) }),
  createOwner: (body) => j("/auth/users/owner", { method: "POST", body: JSON.stringify(body) }),
  users: () => j("/auth/users"),
};

export const api = {
  tenants: () => j("/admin/tenants"),
  tenant: (tq = "") => j(`/admin/tenant${tq}`),
  createTenant: (body) => j("/admin/tenants", { method: "POST", body: JSON.stringify(body) }),
  updateTenant: (body, tq = "") => j(`/admin/tenant${tq}`, { method: "PUT", body: JSON.stringify(body) }),
  products: (tq = "") => j(`/admin/products${tq}`),
  saveProduct: (body, tq = "") => j(`/admin/products${tq}`, { method: "POST", body: JSON.stringify(body) }),
  deleteProduct: (pid, tq = "") => j(`/admin/products/${pid}${tq}`, { method: "DELETE" }),
  orders: (tq = "") => j(`/admin/orders${tq}`),
  setOrderEstado: (oid, estado, tq = "") => j(`/admin/orders/${oid}${tq}`, { method: "PATCH", body: JSON.stringify({ estado }) }),
  metrics: (tq = "") => j(`/admin/metrics${tq}`),
  overview: () => j("/admin/overview"),
};

export const rd = (n) => `RD$${(n ?? 0).toLocaleString("es-DO")}`;
