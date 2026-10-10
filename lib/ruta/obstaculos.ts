import type { ObstaculosDato, Punto } from "../tipos";
import obstaculosJson from "@/data/obstaculos.json";

const OBS = obstaculosJson as unknown as ObstaculosDato;

type Seg = [Punto, Punto];

function orient(a: Punto, b: Punto, c: Punto): number {
  const v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
  return v > 0 ? 1 : v < 0 ? -1 : 0;
}
const enSegmento = (a: Punto, b: Punto, p: Punto) =>
  Math.min(a[0], b[0]) <= p[0] && p[0] <= Math.max(a[0], b[0]) && Math.min(a[1], b[1]) <= p[1] && p[1] <= Math.max(a[1], b[1]);

/** los segmentos se cortan o se tocan */
function segmentosSeCortan([a, b]: Seg, [c, d]: Seg): boolean {
  const o1 = orient(a, b, c);
  const o2 = orient(a, b, d);
  const o3 = orient(c, d, a);
  const o4 = orient(c, d, b);
  if (o1 !== o2 && o3 !== o4) return true;
  return (
    (o1 === 0 && enSegmento(a, b, c)) ||
    (o2 === 0 && enSegmento(a, b, d)) ||
    (o3 === 0 && enSegmento(c, d, a)) ||
    (o4 === 0 && enSegmento(c, d, b))
  );
}

/** punto dentro del polígono (anillo exterior y huecos, regla par-impar) */
function dentroDe(anillos: number[][][], p: Punto): boolean {
  let dentro = false;
  for (const anillo of anillos) {
    for (let i = 0, j = anillo.length - 1; i < anillo.length; j = i++) {
      const [xi, yi] = anillo[i];
      const [xj, yj] = anillo[j];
      if (yi > p[1] !== yj > p[1] && p[0] < ((xj - xi) * (p[1] - yi)) / (yj - yi) + xi) dentro = !dentro;
    }
  }
  return dentro;
}

function cruzaPoligono(anillos: number[][][], segs: Seg[]): boolean {
  for (const s of segs) if (dentroDe(anillos, s[0])) return true;
  for (const anillo of anillos) {
    for (let i = 0; i + 1 < anillo.length; i++) {
      const borde: Seg = [anillo[i] as Punto, anillo[i + 1] as Punto];
      for (const s of segs) if (segmentosSeCortan(s, borde)) return true;
    }
  }
  return false;
}

/**
 * ¿La polilínea atraviesa algún obstáculo (sin inflar)? Mismo criterio que pipeline/ruta.py: muebles, postes y obstáculos extra
 * (muestreo cada 1 pt, con 0,5 pt de tolerancia) y las barreras de módulos (polígonos reducidos 0,5 pt).
 */
export function cruzaObstaculos(puntos: Punto[]): boolean {
  const segs: Seg[] = [];
  for (let i = 0; i + 1 < puntos.length; i++) segs.push([puntos[i], puntos[i + 1]]);
  if (OBS.poligonos.some((p) => cruzaPoligono(p, segs))) return true;
  for (const [a, b] of segs) {
    const n = Math.max(2, Math.trunc(Math.hypot(b[0] - a[0], b[1] - a[1])));
    for (let i = 0; i <= n; i++) {
      const x = a[0] + ((b[0] - a[0]) * i) / n;
      const y = a[1] + ((b[1] - a[1]) * i) / n;
      for (const [, r] of OBS.rects) {
        if (r[0] + 0.5 < x && x < r[2] - 0.5 && r[1] + 0.5 < y && y < r[3] - 0.5) return true;
      }
    }
  }
  return false;
}
