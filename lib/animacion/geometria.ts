import type { Punto } from "../tipos";

/** Polilínea con longitud acumulada: da el punto a una distancia s del inicio (sin depender del DOM, así se puede probar). */
export class Polilinea {
  readonly largo: number;
  private readonly acum: number[] = [0];

  constructor(readonly puntos: readonly Punto[]) {
    for (let i = 1; i < puntos.length; i++) {
      this.acum.push(this.acum[i - 1] + Math.hypot(puntos[i][0] - puntos[i - 1][0], puntos[i][1] - puntos[i - 1][1]));
    }
    this.largo = this.acum[this.acum.length - 1];
  }

  puntoEn(s: number): Punto {
    const p = this.puntos;
    if (s <= 0) return [p[0][0], p[0][1]];
    if (s >= this.largo) return [p[p.length - 1][0], p[p.length - 1][1]];
    let i = 1;
    while (this.acum[i] < s) i++;
    const l = this.acum[i] - this.acum[i - 1] || 1;
    const u = (s - this.acum[i - 1]) / l;
    return [p[i - 1][0] + (p[i][0] - p[i - 1][0]) * u, p[i - 1][1] + (p[i][1] - p[i - 1][1]) * u];
  }

  /** atributo `d` de un <path> */
  trazo(): string {
    return "M" + this.puntos.map((q) => `${q[0]},${q[1]}`).join(" L");
  }
}

export const suave = (u: number) => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2);

/** El mapa se muestra girado 90° (la entrada abajo): plano (x, y) → pantalla (x', y'). Mismos datos que data/mapa.json. */
export function crearProyeccion(F: readonly [number, number, number, number]) {
  return (x: number, y: number): Punto => [y - F[1], F[2] - x];
}
