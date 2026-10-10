import type { Punto } from "@/lib/tipos";
import { calcularRuta, cruzaObstaculos } from "@/lib/ruta";
import fixtures from "../fixtures/rutas_python.json";

export interface RefPython {
  cara: string;
  mueble: string;
  alterna: boolean;
  puntos: Punto[];
  largo: number;
  cruza: boolean;
  via: Punto | null;
  pasos: string[];
  fin: number[];
  L: number;
}

export interface FilaParidad {
  clave: string;
  caraPy: string;
  caraTs: string;
  ladoContrarioPy: boolean;
  ladoContrarioTs: boolean;
  largoPy: number;
  largoTs: number;
  difPct: number;
  puntosIguales: boolean;
  tramosIguales: boolean;
  textosIguales: boolean;
  cruzaTs: boolean;
}

const refs = (): [string, string, string | undefined, RefPython][] => [
  ...Object.entries(fixtures.destinos as unknown as Record<string, RefPython>).map(
    ([v, r]): [string, string, string | undefined, RefPython] => [v, v, undefined, r],
  ),
  // las 8 caras sin ancla: la clave es "mueble:cara" y se pide esa cara concreta
  ...Object.entries(fixtures.sin_ancla as unknown as Record<string, RefPython>).map(
    ([k, r]): [string, string, string | undefined, RefPython] => {
      const [mueble, cara] = k.split(":");
      return [k, mueble, cara, r];
    },
  ),
];

/** compara la ruta calculada en TypeScript con la de Python (los fixtures) para los 67 pasillos y las 8 caras sin ancla */
export function compararTodas(): FilaParidad[] {
  return refs().map(([clave, destino, cara, py]) => {
    const ts = calcularRuta(destino, cara ? { cara: cara as never } : {});
    const mismosPuntos =
      ts.puntos.length === py.puntos.length && ts.puntos.every((p, i) => p[0] === py.puntos[i][0] && p[1] === py.puntos[i][1]);
    return {
      clave,
      caraPy: py.cara,
      caraTs: ts.cara,
      ladoContrarioPy: py.alterna,
      ladoContrarioTs: ts.ladoContrario,
      largoPy: py.largo,
      largoTs: ts.largo,
      difPct: py.largo === 0 ? 0 : (Math.abs(ts.largo - py.largo) / py.largo) * 100,
      puntosIguales: mismosPuntos,
      tramosIguales: JSON.stringify(ts.tramos) === JSON.stringify(py.fin),
      textosIguales: JSON.stringify(ts.instrucciones) === JSON.stringify(py.pasos),
      cruzaTs: cruzaObstaculos(ts.puntos),
    };
  });
}
