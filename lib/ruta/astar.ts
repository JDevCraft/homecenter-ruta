import type { Celda } from "../tipos";
import type { Cuadricula } from "./cuadricula";

interface Nodo {
  f: number;
  g: number;
  y: number;
  x: number;
}

/** orden de la tupla (f, g, fila, columna): idéntico al heapq de la versión en Python, para que salgan los mismos caminos */
const menor = (a: Nodo, b: Nodo) => a.f - b.f || a.g - b.g || a.y - b.y || a.x - b.x;

class Monticulo {
  private readonly a: Nodo[] = [];
  get vacio() {
    return this.a.length === 0;
  }
  push(n: Nodo) {
    const a = this.a;
    a.push(n);
    let i = a.length - 1;
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (menor(a[i], a[p]) >= 0) break;
      [a[i], a[p]] = [a[p], a[i]];
      i = p;
    }
  }
  pop(): Nodo {
    const a = this.a;
    const top = a[0];
    const ultimo = a.pop() as Nodo;
    if (a.length > 0) {
      a[0] = ultimo;
      let i = 0;
      for (;;) {
        const l = 2 * i + 1;
        const r = l + 1;
        let m = i;
        if (l < a.length && menor(a[l], a[m]) < 0) m = l;
        if (r < a.length && menor(a[r], a[m]) < 0) m = r;
        if (m === i) break;
        [a[i], a[m]] = [a[m], a[i]];
        i = m;
      }
    }
    return top;
  }
}

/** vecinos: (dy, dx, costo). El diagonal cuesta 1,4142, igual que la versión en Python. */
const N8: readonly (readonly [number, number, number])[] = [
  [-1, 0, 1],
  [1, 0, 1],
  [0, -1, 1],
  [0, 1, 1],
  [-1, -1, 1.4142],
  [-1, 1, 1.4142],
  [1, -1, 1.4142],
  [1, 1, 1.4142],
];

/** A* de 8 vecinos, sin cortar esquinas. Devuelve la lista de celdas de `inicio` a la primera meta alcanzada, o null. */
export function astar(cu: Cuadricula, inicio: Celda, metas: Celda[]): Celda[] | null {
  const nx = cu.nx;
  const llave = (y: number, x: number) => y * nx + x;
  const esMeta = new Set(metas.map((m) => llave(m[0], m[1])));
  const h = (y: number, x: number) => {
    let mejor = Infinity;
    for (const m of metas) mejor = Math.min(mejor, Math.hypot(y - m[0], x - m[1]));
    return mejor;
  };
  const g = new Map<number, number>([[llave(inicio[0], inicio[1]), 0]]);
  const padre = new Map<number, number>();
  const cola = new Monticulo();
  cola.push({ f: h(inicio[0], inicio[1]), g: 0, y: inicio[0], x: inicio[1] });
  while (!cola.vacio) {
    const { g: gc, y, x } = cola.pop();
    const k = llave(y, x);
    if (esMeta.has(k)) {
      const camino: Celda[] = [[y, x]];
      let c = k;
      while (padre.has(c)) {
        c = padre.get(c) as number;
        camino.push([Math.floor(c / nx), c % nx]);
      }
      return camino.reverse();
    }
    if (gc > (g.get(k) ?? Infinity)) continue;
    for (const [dy, dx, w] of N8) {
      const ny = y + dy;
      const nxx = x + dx;
      if (cu.bloqueada(ny, nxx)) continue;
      if (dy !== 0 && dx !== 0 && (cu.bloqueada(y + dy, x) || cu.bloqueada(y, x + dx))) continue;
      const ng = gc + w;
      const kn = llave(ny, nxx);
      if (ng < (g.get(kn) ?? 1e18)) {
        g.set(kn, ng);
        padre.set(kn, k);
        cola.push({ f: ng + h(ny, nxx), g: ng, y: ny, x: nxx });
      }
    }
  }
  return null;
}
