import { NextResponse, type NextRequest } from "next/server";
import { buscarProductos } from "@/lib/buscador";
import { pasillosDelPlano } from "@/lib/ruta";

/** el catálogo y su índice se cargan una sola vez por instancia del servidor (módulo), no en cada petición */
const PLANO = new Set(pasillosDelPlano());
const MAX_Q = 80;

export interface ProductoPublico {
  sku: string;
  descripcion: string;
  familia: string;
  /** pasillo principal tal como viene en el catálogo (p. ej. "13B"); "" si no tiene */
  pasillo: string;
  /** ID del plano si el pasillo existe en el mapa; null si el producto está fuera del plano */
  idPlano: string | null;
  alternativas: { pasillo: string; idPlano: string | null }[];
}

export interface RespuestaBuscar {
  q: string;
  resultados: ProductoPublico[];
  sugerencias: string[];
  /** mensaje para el cliente cuando no hay resultados o la consulta es muy corta */
  mensaje: string | null;
}

const idDePlano = (pasillo: string) => (PLANO.has(pasillo.toLowerCase()) ? pasillo.toLowerCase() : null);

function responder(cuerpo: RespuestaBuscar) {
  return NextResponse.json(cuerpo, { headers: { "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400" } });
}

/** GET /api/buscar?q=pintura blanco almendra → los 5 mejores resultados (solo campos públicos) */
export function GET(request: NextRequest) {
  const q = (request.nextUrl.searchParams.get("q") ?? "").trim().slice(0, MAX_Q);
  if (q.replace(/\s+/g, "").length < 2) {
    return responder({ q, resultados: [], sugerencias: [], mensaje: "Escribe al menos 2 letras para buscar un producto." });
  }
  const r = buscarProductos(q, 5);
  const resultados: ProductoPublico[] = r.resultados.map((x) => ({
    sku: x.sku,
    descripcion: x.descripcion,
    familia: x.familia,
    pasillo: x.pasillo,
    idPlano: x.idPlano,
    alternativas: x.alternativas.map((p) => ({ pasillo: p, idPlano: idDePlano(p) })),
  }));
  return responder({
    q,
    resultados,
    sugerencias: r.sugerencias,
    mensaje: resultados.length === 0 ? `No encontré productos para «${q}».` : null,
  });
}
