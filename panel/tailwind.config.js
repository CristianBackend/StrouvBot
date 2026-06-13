/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx}", "./components/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0B0710",        // fondo casi negro, tono violáceo
        surface: "#16101F",    // tarjetas / superficies
        "surface-2": "#1E1630",
        line: "#2A2140",        // bordes sutiles
        strouv: {
          DEFAULT: "#8B5CF6",  // morado de acción
          light: "#C4B5FD",    // acento claro
          magenta: "#D946EF",  // solo para el gradiente de marca
        },
        ok: "#34D399",          // pagado
        warn: "#FBBF24",        // pendiente
        muted: "#8B82A3",       // texto secundario
      },
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        body: ["var(--font-body)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(139,92,246,0.25), 0 8px 40px -12px rgba(139,92,246,0.45)",
      },
      backgroundImage: {
        brand: "linear-gradient(120deg, #8B5CF6 0%, #D946EF 100%)",
      },
    },
  },
  plugins: [],
};
