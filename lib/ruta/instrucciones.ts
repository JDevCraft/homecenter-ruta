import type { Caja, Punto } from "../tipos";
import datos from "@/data/instrucciones.json";

/**
 * Texto de las indicaciones de una ruta (máximo 5 pasos) y punto donde termina cada paso.
 * Port de pipeline/mapa_cliente.py: mismas reglas y mismos textos. La página ya no muestra las indicaciones,
 * pero los puntos donde terminan los pasos son los tramos de la animación.
 */

interface Hito {
  id: string;
  nombre: string;
  pos: Punto;
  rect: Caja | null;
}
interface Barrera {
  i: number;
  j: number;
  lo: number;
  hi: number;
  span: [number, number];
}

const HITOS = datos.hitos as Hito[];
const HITO_RECT = new Map<string, Caja>(HITOS.filter((h) => h.rect).map((h) => [h.id, h.rect as Caja]));
const MUEBLES = datos.muebles as { v: string; bbox: Caja }[];
const BARRERAS = datos.barreras as Barrera[];
const PC = datos.pc as { x0: number; y0: number; x1: number; y1: number; banda: [number, number] };
const TOL = 8;

export const cajaFusionada = (muebleId: string): Caja => (datos.fusionados as unknown as Record<string, Caja>)[muebleId];

const distPuntoCaja = (p: Punto, b: Caja) => Math.hypot(Math.max(b[0] - p[0], 0, p[0] - b[2]), Math.max(b[1] - p[1], 0, p[1] - b[3]));

function muestras(a: Punto, b: Punto, paso = 20): Punto[] {
  const n = Math.max(1, Math.trunc(Math.hypot(b[0] - a[0], b[1] - a[1]) / paso));
  const r: Punto[] = [];
  for (let i = 0; i <= n; i++) r.push([a[0] + ((b[0] - a[0]) * i) / n, a[1] + ((b[1] - a[1]) * i) / n]);
  return r;
}

type Candidato = [number, string, string];

function candidatos(a: Punto, b: Punto, excluir: Set<string | null>): Candidato[] {
  const pts = muestras(a, b);
  const out: Candidato[] = [];
  for (const h of HITOS) {
    if (excluir.has(h.id)) continue;
    const rect = HITO_RECT.get(h.id);
    const d = Math.min(...pts.map((p) => (rect ? distPuntoCaja(p, rect) : Math.hypot(p[0] - h.pos[0], p[1] - h.pos[1]))));
    if (d <= 70) out.push([d - 25, h.id, h.nombre]); // los hitos pesan más que una góndola
  }
  for (const m of MUEBLES) {
    if (excluir.has(m.v)) continue;
    const d = Math.min(...pts.map((p) => distPuntoCaja(p, m.bbox)));
    if (d <= 60) out.push([d, m.v, `la góndola ${m.v}`]);
  }
  // sorted(set(...)) de Python: sin repetidos, por (distancia, id, nombre)
  const unicos = new Map(out.map((c) => [`${c[0]}|${c[1]}|${c[2]}`, c]));
  return [...unicos.values()].sort(
    (p, q) => p[0] - q[0] || (p[1] < q[1] ? -1 : p[1] > q[1] ? 1 : 0) || (p[2] < q[2] ? -1 : p[2] > q[2] ? 1 : 0),
  );
}

const clave = (p: Punto) => `${p[0]},${p[1]}`;

function simplificar(pts: Punto[], maxTramos: number, fijos: Set<string>): Punto[] {
  const r = [...pts];
  const area = (i: number) => {
    const [[x0, y0], [x1, y1], [x2, y2]] = [r[i - 1], r[i], r[i + 1]];
    return Math.abs((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)) / 2;
  };
  while (r.length - 1 > maxTramos && r.length > 2) {
    let mejor = -1;
    let mejorArea = Infinity;
    for (let i = 1; i < r.length - 1; i++) {
      if (fijos.has(clave(r[i]))) continue; // los extremos de cruces y esquinas del pasillo central no se quitan
      const a = area(i);
      if (a < mejorArea) {
        mejorArea = a;
        mejor = i;
      }
    }
    if (mejor < 0) break;
    r.splice(mejor, 1);
  }
  return r;
}

const giro = (a: Punto, b: Punto, c: Punto) => {
  const d1 = [b[0] - a[0], b[1] - a[1]];
  const d2 = [c[0] - b[0], c[1] - b[1]];
  return (Math.atan2(d1[0] * d2[1] - d1[1] * d2[0], d1[0] * d2[0] + d1[1] * d2[1]) * 180) / Math.PI;
};

const esPasilloCentral = (a: Punto, b: Punto) =>
  PC.x0 - 80 <= Math.min(a[0], b[0]) &&
  Math.max(a[0], b[0]) <= PC.x1 + 40 &&
  Math.abs(b[0] - a[0]) >= 100 &&
  PC.banda[0] <= a[1] &&
  a[1] <= PC.banda[1] + 40 &&
  PC.banda[0] <= b[1] &&
  b[1] <= PC.banda[1] + 40 &&
  Math.abs(b[1] - a[1]) <= 0.6 * Math.abs(b[0] - a[0]);

function cruzaBarrera(a: Punto, b: Punto): Barrera | null {
  for (const br of BARRERAS) {
    const { i, j } = br;
    const m = (a[j] + b[j]) / 2;
    if (!(br.span[0] <= m && m <= br.span[1])) continue;
    if ((a[i] <= br.lo + TOL && b[i] >= br.hi - TOL) || (b[i] <= br.lo + TOL && a[i] >= br.hi - TOL)) return br;
  }
  return null;
}

const largoPt = (a: Punto, b: Punto) => Math.hypot(b[0] - a[0], b[1] - a[1]);

type Ref = [string | null, string | null, string | null];

/** una sola ruta a la vez: los puntos de referencia ya nombrados no se repiten ni en pasos no consecutivos */
class Referencias {
  private readonly usados = new Set<string>();

  private cand(a: Punto, b: Punto, excluir: Set<string | null>) {
    return candidatos(a, b, excluir);
  }

  private ref(a: Punto, b: Punto, destino: string, previo: string | null): Ref {
    const base = new Set<string | null>([destino, previo]);
    const conUsados = new Set<string | null>([...base, ...this.usados]);
    let c = this.cand(a, b, conUsados).filter((x) => x[1] !== previo);
    if (c.length === 0) c = this.cand(a, b, base).filter((x) => x[1] !== previo);
    if (c.length > 0) {
      this.usados.add(c[0][1]);
      return ["junto a", c[0][2], c[0][1]];
    }
    if (this.cand(a, b, new Set<string | null>([previo])).some((x) => x[1] === destino)) {
      return ["hasta", `la góndola ${destino}`, destino];
    }
    return [null, null, previo];
  }

  /** (preposición, texto, id): el destino solo si no hay otra cosa, nunca repite el previo; en tramos largos (>500 pt) nombra dos puntos */
  referenciaTramo(a: Punto, b: Punto, destino: string, previo: string | null): Ref {
    if (largoPt(a, b) > 500) {
      const m: Punto = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
      const [p1, t1, id1] = this.ref(a, m, destino, previo);
      const [p2, t2, id2] = this.ref(m, b, destino, id1);
      if (t1 && t2 && p1 === "junto a" && p2 === "junto a" && id1 !== id2) return ["junto a", `${t1} y después junto a ${t2}`, id2];
      if (t2 && !t1) return [p2, t2, id2];
      if (t1) return [p1, t1, id1];
    }
    return this.ref(a, b, destino, previo);
  }

  refTxt(a: Punto, b: Punto, destino: string, previo: string | null): [string, string | null] {
    const [prep, donde, id] = this.referenciaTramo(a, b, destino, previo);
    return [donde ? `${prep} ${donde}` : "por el pasillo", id];
  }
}

function construirPasos(pts: Punto[], iv: number | null, destino: string): { pasos: string[]; fines: Punto[] } {
  const R = new Referencias();
  const pasos: string[] = [];
  const fines: Punto[] = [];
  const poner = (txt: string, fin: Punto) => {
    pasos.push(txt);
    fines.push(fin);
  };
  let previo: string | null = null;
  let i = 0;
  if (iv !== null && iv >= 1) {
    // todo el recorrido compartido hasta el pasillo central de la zona c se cuenta como un solo paso
    const [p1, t1, id1] = R.referenciaTramo(pts[0], pts[1], destino, null);
    const [p2, t2, id2]: Ref = iv >= 2 ? R.referenciaTramo(pts[iv - 1], pts[iv], destino, id1) : [null, null, id1];
    const partes: string[] = [];
    if (t1) partes.push(`avanza ${p1} ${t1}`);
    if (t2 && id2 !== id1 && p2 === "junto a") partes.push(`baja por el pasillo de ${t2}`);
    poner(
      partes.length > 0
        ? `Desde la entrada, ${partes.join(" y ")} hasta el pasillo central de la zona c.`
        : "Desde la entrada, ve hasta el pasillo central de la zona c.",
      pts[iv],
    );
    previo = id2 || id1;
    i = iv;
  }
  while (i < pts.length - 1) {
    let a = pts[i];
    const b = pts[i + 1];
    const br = cruzaBarrera(a, b);
    if (esPasilloCentral(a, b)) {
      // pasillo central + bajada por el pasillo de la góndola = un solo paso
      let j = i + 1;
      while (j + 1 < pts.length && esPasilloCentral(pts[j], pts[j + 1])) j++;
      if (j + 1 < pts.length && pts[j + 1][1] - pts[j][1] > 40) {
        poner(`Sigue por el pasillo central de la zona c y baja por el pasillo de la góndola ${destino}.`, pts[j + 1]);
        i = j + 1;
        continue;
      }
      poner("Sigue por el pasillo central de la zona c.", pts[j]);
      i = j;
      continue;
    }
    if (br) {
      // el cruce entre los módulos y el tramo siguiente se cuentan como un solo paso
      const k = br.i;
      const sentido = a[k] < b[k] ? 1 : -1;
      const borde = sentido > 0 ? br.lo : br.hi;
      if (Math.abs(a[k] - borde) > 120) {
        // tramo largo que solo cruza al final: primero se describe el recorrido hasta la barrera
        const t = (borde - 12 * sentido - a[k]) / (b[k] - a[k]);
        const a2: Punto = [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])];
        const [ref, prev] = R.refTxt(a, a2, destino, previo);
        previo = prev;
        if (pasos.length === 0) poner(`Desde la entrada, avanza ${ref}.`, a2);
        else poner(`Gira a la ${giro(pts[i - 1], a, b) > 0 ? "derecha" : "izquierda"} y sigue ${ref}.`, a2);
        a = a2;
      }
      if (i + 2 < pts.length) {
        const c = pts[i + 2];
        const dx = c[0] - b[0];
        const dy = c[1] - b[1];
        const verbo = Math.abs(dy) >= Math.abs(dx) ? (dy > 0 ? "baja" : "sube") : "sigue";
        const [ref, prev] = R.refTxt(b, c, destino, previo);
        previo = prev;
        poner(`Cruza entre los módulos de exhibición y ${verbo} ${ref}.`, c);
        i += 2;
        continue;
      }
      const resto = Math.abs(b[k] - (sentido > 0 ? br.hi : br.lo));
      if (resto > 60) {
        // el mismo tramo sigue más allá de la barrera hasta la góndola
        const verbo = k === 1 ? (sentido > 0 ? "baja" : "sube") : "sigue";
        poner(`Cruza entre los módulos de exhibición y ${verbo} hasta la góndola ${destino}.`, b);
      } else {
        poner("Cruza entre los módulos de exhibición.", b);
      }
      i += 1;
      continue;
    }
    const [ref, prev] = R.refTxt(a, b, destino, previo);
    previo = prev;
    if (pasos.length === 0) poner(`Desde la entrada, avanza ${ref}.`, b);
    else poner(`Gira a la ${giro(pts[i - 1], a, b) > 0 ? "derecha" : "izquierda"} y sigue ${ref}.`, b);
    i += 1;
  }
  return { pasos, fines };
}

export interface EntradaInstrucciones {
  puntos: Punto[];
  via: Punto | null;
  ladoContrario: boolean;
}

/** máximo 5 pasos por ruta (salida + giros + llegada); `fines[k]` es el punto donde termina el paso k */
export function instrucciones(r: EntradaInstrucciones, destino: string, muebleDest: Caja, maxPasos = 5) {
  const pts0 = r.puntos;
  let iv0: number | null = null;
  if (r.via) {
    let mejor = Infinity;
    pts0.forEach((p, i) => {
      const d = Math.hypot(p[0] - (r.via as Punto)[0], p[1] - (r.via as Punto)[1]);
      if (d < mejor) {
        mejor = d;
        iv0 = i;
      }
    });
    if (mejor > 12) iv0 = null;
  }
  const lim: Punto[] = [];
  pts0.forEach((p, i) => {
    if (i > 0 && i < pts0.length - 1 && i !== iv0 && Math.abs(giro(lim[lim.length - 1], p, pts0[i + 1])) < 30) return;
    lim.push(p);
  });
  const fijos = new Set<string>();
  for (let i = 0; i + 1 < lim.length; i++) {
    if (cruzaBarrera(lim[i], lim[i + 1])) fijos.add(clave(lim[i])).add(clave(lim[i + 1]));
  }
  if (iv0 !== null) fijos.add(clave(pts0[iv0]));
  for (let i = 0; i + 1 < lim.length; i++) {
    if (esPasilloCentral(lim[i], lim[i + 1])) fijos.add(clave(lim[i])).add(clave(lim[i + 1])); // esquinas del pasillo central
  }
  let pts: Punto[] = lim;
  let pasos: string[] = [];
  let fines: Punto[] = [];
  for (const maxl of [4, 3, 2, 1]) {
    pts = simplificar(lim, maxl, fijos);
    const iv = iv0 !== null ? pts.findIndex((p) => clave(p) === clave(pts0[iv0 as number])) : -1;
    ({ pasos, fines } = construirPasos(pts, iv >= 0 ? iv : null, destino));
    if (pasos.length + 1 <= maxPasos) break;
  }
  // llegada: lado en que queda la góndola respecto a la dirección final
  const a = pts[pts.length - 2];
  const b = pts[pts.length - 1];
  const cx = (muebleDest[0] + muebleDest[2]) / 2;
  const cy = (muebleDest[1] + muebleDest[3]) / 2;
  const h = [b[0] - a[0], b[1] - a[1]];
  const v = [cx - b[0], cy - b[1]];
  const cruz = h[0] * v[1] - h[1] * v[0];
  const punto = h[0] * v[0] + h[1] * v[1];
  const n = Math.hypot(h[0], h[1]) * Math.hypot(v[0], v[1]) || 1;
  const pos = Math.abs(cruz) / n < 0.35 && punto > 0 ? "frente a ti" : cruz > 0 ? "a tu derecha" : "a tu izquierda";
  pasos.push(`Llegaste: la góndola ${destino} queda ${pos}.`);
  fines.push(b);
  if (r.ladoContrario) pasos[pasos.length - 1] += " Tu producto está en el lado contrario de esta góndola: rodéala; el mapa lo marca.";
  return { pasos, fines };
}

/** longitud recorrida sobre la polilínea hasta el punto más cercano a p */
function largoHasta(pts: Punto[], p: Punto): number {
  let mejor = 1e18;
  let acum = 0;
  let mejorLen = 0;
  for (let i = 0; i + 1 < pts.length; i++) {
    const [x0, y0] = pts[i];
    const [x1, y1] = pts[i + 1];
    const dx = x1 - x0;
    const dy = y1 - y0;
    const l2 = dx * dx + dy * dy;
    const t = l2 === 0 ? 0 : Math.max(0, Math.min(1, ((p[0] - x0) * dx + (p[1] - y0) * dy) / l2));
    const d = Math.hypot(x0 + t * dx - p[0], y0 + t * dy - p[1]);
    const l = Math.sqrt(l2);
    if (d <= mejor + 1e-6) {
      mejor = d;
      mejorLen = acum + t * l;
    }
    acum += l;
  }
  return mejorLen;
}

const redondear1 = (v: number) => Math.round(v * 10) / 10;

/** tramos de la animación: longitud acumulada donde termina cada paso (el último valor es la llegada) */
export function tramosDe(puntos: Punto[], fines: Punto[]): number[] {
  const total = puntos.slice(1).reduce((s, p, i) => s + Math.hypot(p[0] - puntos[i][0], p[1] - puntos[i][1]), 0);
  const fin: number[] = [];
  let prev = 0;
  for (const f of fines) {
    const v = Math.max(prev, largoHasta(puntos, f));
    fin.push(redondear1(v));
    prev = v;
  }
  fin[fin.length - 1] = redondear1(total);
  if (fin.length > 1 && fin[fin.length - 2] > total - 25) fin[fin.length - 2] = redondear1(total); // el último tramo de camino llega al destino
  return fin;
}

/** tramos de una ruta sin texto (rutas desde otro pasillo): vértices con giro ≥ 30°, máximo 4 tramos */
export function tramosPorGiros(puntos: Punto[]): number[] {
  const lim: Punto[] = [];
  puntos.forEach((p, i) => {
    if (i > 0 && i < puntos.length - 1 && Math.abs(giro(lim[lim.length - 1], p, puntos[i + 1])) < 30) return;
    lim.push(p);
  });
  const s = simplificar(lim, 4, new Set());
  const total = puntos.slice(1).reduce((t, p, i) => t + Math.hypot(p[0] - puntos[i][0], p[1] - puntos[i][1]), 0);
  const fin: number[] = [];
  let prev = 0;
  for (const p of s.slice(1)) {
    const v = Math.max(prev, largoHasta(puntos, p));
    fin.push(redondear1(v));
    prev = v;
  }
  if (fin.length === 0) fin.push(redondear1(total));
  fin[fin.length - 1] = redondear1(total);
  return [...fin, redondear1(total)];
}
