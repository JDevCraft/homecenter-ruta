import type { Celda, GridDato, Punto } from "../tipos";

/** Cuadrícula de ocupación precalculada (margen de carro y cierre de módulos ya aplicados en el pipeline). */
export class Cuadricula {
  readonly paso: number;
  readonly nx: number;
  readonly ny: number;
  readonly x0: number;
  readonly y0: number;
  private readonly bloq: Uint8Array;

  constructor(g: GridDato) {
    this.paso = g.paso;
    this.nx = g.nx;
    this.ny = g.ny;
    this.x0 = g.x0;
    this.y0 = g.y0;
    const bin = atob(g.bits);
    this.bloq = new Uint8Array(g.nx * g.ny);
    for (let i = 0; i < this.bloq.length; i++) {
      this.bloq[i] = (bin.charCodeAt(i >> 3) >> (7 - (i & 7))) & 1;
    }
  }

  dentro(y: number, x: number): boolean {
    return y >= 0 && y < this.ny && x >= 0 && x < this.nx;
  }

  /** true si la celda está ocupada; fuera de la cuadrícula cuenta como ocupada */
  bloqueada(y: number, x: number): boolean {
    return !this.dentro(y, x) || this.bloq[y * this.nx + x] === 1;
  }

  libres(): number {
    let n = 0;
    for (const b of this.bloq) if (b === 0) n++;
    return n;
  }

  /** centro de la celda en puntos del plano */
  centro(c: Celda): Punto {
    return [this.x0 + (c[1] + 0.5) * this.paso, this.y0 + (c[0] + 0.5) * this.paso];
  }
}
