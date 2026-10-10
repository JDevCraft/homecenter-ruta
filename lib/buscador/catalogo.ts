import catalogoJson from "@/data/catalogo.json";
import gridJson from "@/data/grid.json";
import { Indice, type Producto } from "./indice";

/** data/catalogo.json: tablas de conjunto y familia + filas [sku, descripción, conjunto, familia, [pasillos]]. Solo campos públicos. */
interface CatalogoDato {
  c: string[];
  f: string[];
  p: [string, string, number, number, string[]][];
}
const CAT = catalogoJson as unknown as CatalogoDato;
const PLANO = new Set<string>((gridJson as { ids: string[] }).ids);

export interface Resultado {
  sku: string;
  descripcion: string;
  conjunto: string;
  familia: string;
  /** pasillo principal tal como viene en el catálogo (p. ej. "13B"); "" si no tiene */
  pasillo: string;
  /** ID del plano ("13b") si el pasillo existe en el mapa; null si no */
  idPlano: string | null;
  /** otras ubicaciones del mismo SKU */
  alternativas: string[];
  primeraUbicacionEnPlano: boolean;
}

export const productos: readonly Producto[] = CAT.p.map((r) => ({ sku: r[0], desc: r[1], conjunto: CAT.c[r[2]], familia: CAT.f[r[3]] }));
const pasillosDe = (i: number) => CAT.p[i][4];

/** pasillo principal = el primero que existe en el plano; el resto son alternativas (se muestra la primera ubicación, sin repetir) */
function resultado(i: number): Resultado {
  const [sku, desc, ci, fi] = CAT.p[i];
  const orden: string[] = [];
  const vistos = new Set<string>();
  for (const x of pasillosDe(i)) {
    const l = x.toLowerCase();
    if (!vistos.has(l)) {
      vistos.add(l);
      orden.push(x);
    }
  }
  const elegido = orden.find((x) => PLANO.has(x.toLowerCase()));
  return {
    sku,
    descripcion: desc,
    conjunto: CAT.c[ci],
    familia: CAT.f[fi],
    pasillo: elegido ?? orden[0] ?? "",
    idPlano: elegido ? elegido.toLowerCase() : null,
    alternativas: orden.filter((x) => x !== elegido).map((x) => x || "(sin pasillo)"),
    primeraUbicacionEnPlano: orden.length > 0 && PLANO.has(orden[0].toLowerCase()),
  };
}

let indice: Indice | null = null;
/** el índice se arma una sola vez por instancia del servidor */
function indiceDelCatalogo(): Indice {
  indice ??= new Indice(productos);
  return indice;
}

export interface RespuestaBusqueda {
  tipo: string;
  resultados: Resultado[];
  sugerencias: string[];
}

/** los 5 mejores resultados para una consulta de 1 a 4 palabras (o un SKU) */
export function buscarProductos(texto: string, k = 5): RespuestaBusqueda {
  const r = indiceDelCatalogo().buscar(texto, k);
  return { tipo: r.tipo, resultados: r.idx.map(resultado), sugerencias: r.sugerencias };
}
