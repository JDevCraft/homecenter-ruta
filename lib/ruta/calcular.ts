import type { Celda, GridDato, NombreCara, Punto, Ruta, RutaOpciones } from "../tipos";
import gridJson from "@/data/grid.json";
import { astar } from "./astar";
import { Cuadricula } from "./cuadricula";
import { cajaFusionada, instrucciones, tramosDe, tramosPorGiros } from "./instrucciones";
import { suavizar } from "./suavizado";

const G = gridJson as unknown as GridDato;
const CU = new Cuadricula(G);
const ORIGEN: Punto = G.origen;
const ANCLAS = new Map<string, Celda>(G.anclas.map((a) => [`${a[0]}:${a[1]}`, [a[2], a[3]] as Celda]));
const OPUESTA: Record<NombreCara, NombreCara> = { oeste: "este", este: "oeste", norte: "sur", sur: "norte" };
const VISIBLES_DE_MUEBLE = new Map<string, string[]>();
for (const c of G.caras) if (!VISIBLES_DE_MUEBLE.has(c.mueble)) VISIBLES_DE_MUEBLE.set(c.mueble, c.visibles);

const redondear1 = (v: number) => Math.round(v * 10) / 10;

function puntoMedioCara(c: GridDato["caras"][number]): Punto {
  const [x0, y0, x1, y1] = c.bbox;
  const cx = (x0 + x1) / 2;
  const cy = (y0 + y1) / 2;
  return { oeste: [x0, cy], este: [x1, cy], norte: [cx, y0], sur: [cx, y1] }[c.cara] as Punto;
}

interface Resolucion {
  /** caras con paso a las que se puede ir, "mueble:cara" */
  ks: string[];
  ladoContrario: boolean;
  caraPedida: NombreCara | null;
}

/**
 * Qué cara usar. Con un ID visible (o de mueble) sin cara: la más cercana a la entrada (en tramos -N/-S, la de cualquiera de los dos);
 * si esa cara no tiene paso, la contraria. Con cara explícita: esa cara, o la contraria si no tiene paso.
 */
function resolverDestino(id: string, cara?: NombreCara): Resolucion | null {
  if (cara) {
    const k = `${id}:${cara}`;
    if (ANCLAS.has(k)) return { ks: [k], ladoContrario: false, caraPedida: cara };
    const op = `${id}:${OPUESTA[cara]}`;
    return { ks: ANCLAS.has(op) ? [op] : [], ladoContrario: true, caraPedida: cara };
  }
  const caras = G.caras.filter((c) => c.visibles.includes(id));
  if (caras.length === 0) return null;
  let pref = caras[0];
  let mejor = Infinity;
  for (const c of caras) {
    const m = puntoMedioCara(c);
    const d = Math.hypot(m[0] - ORIGEN[0], m[1] - ORIGEN[1]);
    if (d < mejor) {
      mejor = d;
      pref = c;
    }
  }
  const k0 = `${pref.mueble}:${pref.cara}`;
  if (ANCLAS.has(k0)) return { ks: [k0], ladoContrario: false, caraPedida: pref.cara };
  const k1 = `${pref.mueble}:${OPUESTA[pref.cara]}`;
  const ks = ANCLAS.has(k1) ? [k1] : [...ANCLAS.keys()].filter((k) => (VISIBLES_DE_MUEBLE.get(k.split(":")[0]) ?? []).includes(id));
  return { ks, ladoContrario: true, caraPedida: pref.cara };
}

/** los vértices pegados a las cabeceras dentro del pasillo central pasan al eje de la banda */
function centrar(pts: Punto[]): Punto[] {
  const b = G.banda;
  if (!b) return pts;
  const yc = (b[1] + b[3]) / 2;
  return pts.map(([x, y], i): Punto =>
    b[0] - 60 <= x && x <= b[2] + 60 && b[1] + 15 <= y && y <= b[3] + 4 && i > 0 && i < pts.length - 1 ? [x, yc] : [x, y],
  );
}

const mismaCelda = (a: Celda, b: Celda) => a[0] === b[0] && a[1] === b[1];

const largoDe = (pts: Punto[]) => pts.slice(1).reduce((s, p, i) => s + Math.hypot(p[0] - pts[i][0], p[1] - pts[i][1]), 0);

/**
 * Ruta a un pasillo (ID visible, p. ej. "13b") o a una cara concreta de un mueble.
 * Sin `desde`, sale de la entrada y pasa por el punto de paso obligado del pasillo central cuando el destino es del bloque c.
 * Con `desde` (pasillo donde está el cliente), sale del ancla de ese pasillo.
 */
export function calcularRuta(destinoId: string, opciones: RutaOpciones = {}): Ruta {
  const res = resolverDestino(destinoId, opciones.cara);
  if (!res || res.ks.length === 0) throw new Error(`Sin ruta al destino «${destinoId}»`);
  let cam: Celda[] | null = null;
  let kElegida = "";
  let via: GridDato["vias"][number] | undefined;
  let inicio: Celda;
  let desdeCelda: Celda | null = null;
  if (opciones.desde) {
    const rd = resolverDestino(opciones.desde);
    if (!rd || rd.ks.length === 0) throw new Error(`Pasillo de origen desconocido «${opciones.desde}»`);
    desdeCelda = ANCLAS.get(rd.ks[0]) as Celda;
    inicio = desdeCelda;
  } else {
    inicio = G.celda_origen;
    via = G.vias.find((v) => v.destinos.includes(destinoId));
  }
  for (const k of res.ks) {
    const meta = ANCLAS.get(k) as Celda;
    let c: Celda[] | null;
    if (via) {
      const c1 = astar(CU, inicio, [via.celda]);
      const c2 = astar(CU, via.celda, [meta]);
      c = c1 && c2 ? c1.concat(c2.slice(1)) : null;
    } else {
      c = astar(CU, inicio, [meta]);
    }
    if (c && (cam === null || c.length < cam.length)) {
      cam = c;
      kElegida = k;
    }
  }
  if (!cam) throw new Error(`A* sin camino a «${destinoId}»`);
  if (cam.length === 1) cam = [cam[0], cam[0]]; // dos pasillos con la misma ancla: ruta de largo cero
  let sm: Celda[];
  if (via) {
    const i = cam.findIndex((c) => mismaCelda(c, (via as GridDato["vias"][number]).celda));
    sm = suavizar(CU, cam.slice(0, i + 1)).concat(suavizar(CU, cam.slice(i)).slice(1));
  } else {
    sm = suavizar(CU, cam);
  }
  const crudos = opciones.desde ? sm.map((c) => CU.centro(c)) : [ORIGEN, ...sm.slice(1).map((c) => CU.centro(c))];
  const centrados = centrar(crudos);
  const largo = redondear1(largoDe(centrados));
  const puntos = centrados.map((p): Punto => [redondear1(p[0]), redondear1(p[1])]);
  const mueble = kElegida.split(":")[0];
  let tramos: number[];
  let textos: string[] = [];
  if (opciones.desde) {
    tramos = tramosPorGiros(puntos);
  } else {
    const { pasos, fines } = instrucciones(
      { puntos, via: via ? via.pos : null, ladoContrario: res.ladoContrario },
      destinoId,
      cajaFusionada(mueble),
    );
    textos = pasos;
    tramos = tramosDe(puntos, fines);
  }
  return {
    destino: destinoId,
    mueble,
    cara: kElegida,
    caraPedida: res.caraPedida,
    ladoContrario: res.ladoContrario,
    puntos,
    largo,
    tramos,
    instrucciones: textos,
    via: via ? via.pos : null,
  };
}

/** IDs visibles de pasillo que tienen ruta */
export const pasillosDelPlano = (): string[] => [...G.ids];

export const origenEntrada = (): Punto => [...ORIGEN];
