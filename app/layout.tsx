import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Homecenter Calle 80 · Búsqueda en tienda",
  description: "Busca un producto y te marcamos el camino hasta su pasillo.",
  robots: { index: false, follow: false }, // demo privada
  openGraph: {
    title: "Homecenter Calle 80 · Búsqueda en tienda",
    description: "Busca un producto y te marcamos el camino hasta su pasillo.",
    locale: "es_CO",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#041E7E",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
