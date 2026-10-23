import type { Punto } from "../tipos";
import { suave } from "./geometria";

/** Vista del mapa en coordenadas de pantalla (mapa ya girado): centro y ancho; el alto sale de la proporción del contenedor. */
export interface Vista {
  cx: number;
  cy: number;
  w: number;
}

/**
 * Cámara sobre el viewBox del <svg>: cambia solo el atributo (sin re-render de React), con transiciones suaves,
 * pellizco y arrastre. `limites` = viewBox del mapa completo [x, y, w, h].
 */
export class Camara {
  vista: Vista;
  private raf = 0;

  constructor(
    private readonly svg: SVGSVGElement,
    private readonly contenedor: HTMLElement,
    private readonly limites: readonly [number, number, number, number],
    private readonly sinMovimiento: () => boolean,
  ) {
    this.vista = this.completa();
    this.fijar(this.vista);
  }

  private proporcion(): number {
    const r = this.contenedor.getBoundingClientRect();
    return (r.height || 600) / (r.width || 360);
  }

  /** mapa completo, ajustado al contenedor */
  completa(): Vista {
    const [x, y, w, h] = this.limites;
    return { cx: x + w / 2, cy: y + h / 2, w: Math.max(w, h / this.proporcion()) };
  }

  /** ancho de vista que deja unas ~0,62 px por pt: las etiquetas de las góndolas cercanas se leen bien en el celular */
  anchoSeguimiento(): number {
    const px = this.contenedor.getBoundingClientRect().width || 360;
    return Math.min(1000, Math.max(520, px / 0.5));
  }

  private acotar(v: Vista): Vista {
    const [lx, ly, lw, lh] = this.limites;
    const rt = this.proporcion();
    const w = Math.min(Math.max(lw, lh / rt), Math.max(240, v.w));
    const h = w * rt;
    const x0 = lx - 50;
    const x1 = lx + lw + 50;
    const y0 = ly - 50;
    const y1 = ly + lh + 50;
    const cx = w >= x1 - x0 ? (x0 + x1) / 2 : Math.min(x1 - w / 2, Math.max(x0 + w / 2, v.cx));
    const cy = h >= y1 - y0 ? (y0 + y1) / 2 : Math.min(y1 - h / 2, Math.max(y0 + h / 2, v.cy));
    return { cx, cy, w };
  }

  fijar(v: Vista): void {
    this.vista = this.acotar(v);
    const h = this.vista.w * this.proporcion();
    this.svg.setAttribute(
      "viewBox",
      `${(this.vista.cx - this.vista.w / 2).toFixed(1)} ${(this.vista.cy - h / 2).toFixed(1)} ${this.vista.w.toFixed(1)} ${h.toFixed(1)}`,
    );
  }

  parar(): void {
    cancelAnimationFrame(this.raf);
  }

  /** transición suave a otra vista (instantánea con prefers-reduced-motion) */
  irA(hacia: Vista, ms: number, fin?: () => void): void {
    this.parar();
    if (this.sinMovimiento() || ms <= 0) {
      this.fijar(hacia);
      fin?.();
      return;
    }
    const a = { ...this.vista };
    const t0 = performance.now();
    const paso = (ahora: number) => {
      const u = Math.min(1, (ahora - t0) / ms);
      const e = suave(u);
      this.fijar({ cx: a.cx + (hacia.cx - a.cx) * e, cy: a.cy + (hacia.cy - a.cy) * e, w: a.w + (hacia.w - a.w) * e });
      if (u < 1) this.raf = requestAnimationFrame(paso);
      else fin?.();
    };
    paso(t0);
  }

  /** vista que encierra los puntos (en coordenadas de pantalla) con margen `pad` y un ancho mínimo */
  ajustar(puntos: readonly Punto[], pad: number, anchoMin: number): Vista {
    let x0 = Infinity;
    let y0 = Infinity;
    let x1 = -Infinity;
    let y1 = -Infinity;
    for (const [x, y] of puntos) {
      x0 = Math.min(x0, x);
      y0 = Math.min(y0, y);
      x1 = Math.max(x1, x);
      y1 = Math.max(y1, y);
    }
    const rt = this.proporcion();
    return { cx: (x0 + x1) / 2, cy: (y0 + y1) / 2, w: Math.max(anchoMin, x1 - x0 + 2 * pad, (y1 - y0 + 2 * pad) / rt) };
  }

  /** arrastrar, pellizcar y rueda; `alTocar` avisa en cuanto el usuario toca el mapa. Devuelve la función que quita los gestos. */
  gestos(alTocar: () => void): () => void {
    const el = this.contenedor;
    const punteros = new Map<number, { x: number; y: number }>();
    let pellizco: { d: number; w: number } | null = null;

    const bajar = (e: PointerEvent) => {
      if ((e.target as Element).closest("button")) return;
      el.setPointerCapture(e.pointerId);
      punteros.set(e.pointerId, { x: e.clientX, y: e.clientY });
      pellizco = null;
      this.parar();
      alTocar();
    };
    const mover = (e: PointerEvent) => {
      const p = punteros.get(e.pointerId);
      if (!p) return;
      const r = el.getBoundingClientRect();
      const esc = this.vista.w / r.width;
      if (punteros.size === 1) {
        this.fijar({ ...this.vista, cx: this.vista.cx - (e.clientX - p.x) * esc, cy: this.vista.cy - (e.clientY - p.y) * esc });
        p.x = e.clientX;
        p.y = e.clientY;
      } else if (punteros.size === 2) {
        p.x = e.clientX;
        p.y = e.clientY;
        const [a, b] = [...punteros.values()];
        const d = Math.hypot(a.x - b.x, a.y - b.y);
        const mx = (a.x + b.x) / 2 - r.left;
        const my = (a.y + b.y) / 2 - r.top;
        if (pellizco) {
          const rt = this.proporcion();
          const antes = { x: this.vista.cx - this.vista.w / 2 + mx * esc, y: this.vista.cy - (this.vista.w * rt) / 2 + my * esc };
          const w = pellizco.w * (pellizco.d / d);
          const e2 = w / r.width;
          this.fijar({ w, cx: antes.x - mx * e2 + w / 2, cy: antes.y - my * e2 + (w * rt) / 2 });
        } else {
          pellizco = { d, w: this.vista.w };
        }
      }
    };
    const soltar = (e: PointerEvent) => {
      punteros.delete(e.pointerId);
      pellizco = null;
    };
    const rueda = (e: WheelEvent) => {
      e.preventDefault();
      alTocar();
      const r = el.getBoundingClientRect();
      const rt = this.proporcion();
      const m = this.vista.w / r.width;
      const px = this.vista.cx - this.vista.w / 2 + (e.clientX - r.left) * m;
      const py = this.vista.cy - (this.vista.w * rt) / 2 + (e.clientY - r.top) * m;
      const w = this.vista.w * Math.exp(e.deltaY * 0.0012);
      const m2 = w / r.width;
      this.fijar({ w, cx: px - (e.clientX - r.left) * m2 + w / 2, cy: py - (e.clientY - r.top) * m2 + (w * rt) / 2 });
    };
    el.addEventListener("pointerdown", bajar);
    el.addEventListener("pointermove", mover);
    el.addEventListener("pointerup", soltar);
    el.addEventListener("pointercancel", soltar);
    el.addEventListener("wheel", rueda, { passive: false });
    return () => {
      el.removeEventListener("pointerdown", bajar);
      el.removeEventListener("pointermove", mover);
      el.removeEventListener("pointerup", soltar);
      el.removeEventListener("pointercancel", soltar);
      el.removeEventListener("wheel", rueda);
    };
  }
}
