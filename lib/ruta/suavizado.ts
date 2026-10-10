import type { Celda } from "../tipos";
import type { Cuadricula } from "./cuadricula";

/** round() de Python: los .5 van al par más cercano (2,5 → 2; 3,5 → 4). Necesario para reproducir la línea de vista exacta. */
function redondeoPython(x: number): number {
  const f = Math.floor(x);
  const d = x - f;
  if (d < 0.5) return f;
  if (d > 0.5) return f + 1;
  return f % 2 === 0 ? f : f + 1;
}

/** línea de vista entre dos celdas: ningún punto de la recta (ni sus esquinas vecinas) cae en una celda ocupada */
function lineaDeVista(cu: Cuadricula, a: Celda, b: Celda): boolean {
  const n = Math.trunc(Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1])) * 2) + 1;
  for (let i = 0; i <= n; i++) {
    const y = a[0] + ((b[0] - a[0]) * i) / n;
    const x = a[1] + ((b[1] - a[1]) * i) / n;
    if (
      cu.bloqueada(redondeoPython(y), redondeoPython(x)) ||
      cu.bloqueada(Math.trunc(y), redondeoPython(x)) ||
      cu.bloqueada(redondeoPython(y), Math.trunc(x))
    ) {
      return false;
    }
  }
  return true;
}

/** deja solo las celdas necesarias para que cada tramo recto tenga línea de vista */
export function suavizar(cu: Cuadricula, camino: Celda[]): Celda[] {
  const r: Celda[] = [camino[0]];
  let i = 0;
  while (i < camino.length - 1) {
    let j = camino.length - 1;
    while (j > i + 1 && !lineaDeVista(cu, camino[i], camino[j])) j--;
    r.push(camino[j]);
    i = j;
  }
  return r;
}
