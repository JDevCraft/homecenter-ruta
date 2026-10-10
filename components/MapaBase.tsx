import { createElement, memo, type ReactNode } from "react";
import { MAPA, type NodoSvg } from "@/lib/mapa";

/** atributos del SVG en notación de React: stroke-width → strokeWidth, class → className (data-* y aria-* se dejan) */
function propiedades(attrs: Record<string, string>): Record<string, string> {
  const p: Record<string, string> = {};
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") p.className = v;
    else if (k.startsWith("data-") || k.startsWith("aria-")) p[k] = v;
    else p[k.replace(/-([a-z])/g, (_, c: string) => c.toUpperCase())] = v;
  }
  return p;
}

function dibujar(n: NodoSvg, clave: number): ReactNode {
  if (typeof n === "string") return n;
  const [etiqueta, attrs, hijos] = n;
  return createElement(etiqueta, { key: clave, ...propiedades(attrs) }, ...hijos.map(dibujar));
}

/** Mapa base de la tienda (góndolas, zonas, colores por familia, hitos y etiquetas) como SVG de React. No cambia durante la ruta. */
export const MapaBase = memo(function MapaBase() {
  return <>{MAPA.arbol.map(dibujar)}</>;
});
