import mapaJson from "@/data/mapa.json";

/** nodo del SVG del mapa base: texto o [etiqueta, atributos, hijos] (generado por pipeline/exportar_datos.py) */
export type NodoSvg = string | [string, Record<string, string>, NodoSvg[]];

export interface MapaDato {
  /** viewBox del mapa completo, ya girado: [x, y, w, h] */
  viewBox: [number, number, number, number];
  /** giro 90° del plano a pantalla (la entrada abajo) */
  rotm: string;
  /** marco del plano [x0, y0, x1, y1] en puntos */
  F: [number, number, number, number];
  ent: { x: number; y: number };
  origen: [number, number];
  colores: { navy: string; azul: string; amarillo: string; rojo: string; gondola: string };
  leyenda: { nombre: string; color: string }[];
  arbol: NodoSvg[];
}

export const MAPA = mapaJson as unknown as MapaDato;
