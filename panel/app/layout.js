import "./globals.css";
import { Space_Grotesk, Inter } from "next/font/google";
import { AuthProvider } from "@/components/AuthProvider";
import Shell from "@/components/Shell";

const display = Space_Grotesk({ subsets: ["latin"], variable: "--font-display", weight: ["400", "500", "600", "700"] });
const body = Inter({ subsets: ["latin"], variable: "--font-body" });

export const metadata = { title: "Strouv · Panel", description: "Tu asistente de ventas por WhatsApp" };

export default function RootLayout({ children }) {
  return (
    <html lang="es" className={`${display.variable} ${body.variable}`}>
      <body className="font-body min-h-screen">
        <AuthProvider><Shell>{children}</Shell></AuthProvider>
      </body>
    </html>
  );
}
