import type { Punto, Ruta } from "../tipos";
import { Camara, type Vista } from "./camara";
import { Polilinea, suave } from "./geometria";
import { ZOOM_OUT, crearLineaDeTiempo, type LineaDeTiempo } from "./linea-de-tiempo";

interface ElementosRuta {
  base: SVGPathElement;
  linea: SVGPathElement;
  tramo: SVGPathElement;
  punta: SVGCircleElement;
  destino: SVGGElement;
}

export interface OpcionesAnimador {
  ruta: Ruta;
  camara: Camara;
  elementos: ElementosRuta;
  /** plano → pantalla (mapa girado) */
  aPantalla: (x: number, y: number) => Punto;
  /** puntos del plano que deben caber al final (la góndola destino y la etiqueta «Estás aquí») */
  puntosFinales: Punto[];
  sinMovimiento: () => boolean;
  /** pinta o quita el resaltado de la góndola destino */
  resaltar: (on: boolean) => void;
  /** se avisa cada vez que cambia el tramo activo (0 … n-1; el último es la llegada) */
  alCambiarPaso: (i: number, n: number) => void;
}

/**
 * Anima el dibujo de la ruta (stroke-dasharray/dashoffset), con cámara que sigue la punta, pausa en cada giro,
 * zoom out final y marcador de destino con pulsos. Solo toca atributos del DOM: no vuelve a renderizar React.
 */
export class Animador {
  private readonly poly: Polilinea;
  private readonly lt: LineaDeTiempo;
  private readonly n: number;
  private readonly finales: number[];
  private readonly ancho: number;
  private readonly ajuste: Vista;
  private raf = 0;
  private t0 = 0;
  private actual = -1;
  private final = false;
  private hecho = false;
  private activo = true;

  constructor(private readonly o: OpcionesAnimador) {
    this.poly = new Polilinea(o.ruta.puntos);
    const L = this.poly.largo;
    this.n = o.ruta.tramos.length;
    const fin = o.ruta.tramos.slice(0, -1);
    this.finales = fin.length > 0 ? [...fin.slice(0, -1), L] : [L];
    this.lt = crearLineaDeTiempo(L, this.finales);
    this.ancho = o.camara.anchoSeguimiento();
    this.ajuste = o.camara.ajustar(o.puntosFinales.map(([x, y]) => o.aPantalla(x, y)), 120, 520);
    for (const el of [o.elementos.linea, o.elementos.base]) {
      el.setAttribute("stroke-dasharray", `${L} ${L}`);
      el.style.strokeDashoffset = String(L);
    }
  }

  /** duración del dibujo con pausas (s) */
  get duracion(): number {
    return this.lt.T;
  }

  iniciar(): void {
    const { camara, sinMovimiento, aPantalla } = this.o;
    if (sinMovimiento()) {
      this.terminar(true);
      return;
    }
    const [sx, sy] = aPantalla(this.poly.puntos[0][0], this.poly.puntos[0][1]);
    camara.fijar({ cx: sx, cy: sy, w: this.ancho });
    this.t0 = performance.now();
    const cuadro = (ahora: number) => {
      if (!this.activo || this.hecho) return;
      const t = (ahora - this.t0) / 1000;
      const fin = this.lt.T + ZOOM_OUT;
      this.pintar(Math.min(t, fin));
      if (t < fin) this.raf = requestAnimationFrame(cuadro);
      else this.hecho = true;
    };
    cuadro(this.t0);
  }

  /** instante t de la animación (se usa en el bucle y en las pruebas) */
  pintar(t: number): void {
    const { camara, elementos } = this.o;
    const s = this.lt.sAt(t);
    const L = this.poly.largo;
    for (const el of [elementos.linea, elementos.base]) el.style.strokeDashoffset = String(L - s);
    if (t < this.lt.T) {
      const [x, y] = this.poly.puntoEn(s);
      elementos.punta.setAttribute("cx", String(x));
      elementos.punta.setAttribute("cy", String(y));
      const i = this.lt.tramoAt(t);
      if (i !== this.actual) this.marcar(i);
      camara.fijar(this.seguir(t));
    } else {
      const u = Math.min(1, (t - this.lt.T) / ZOOM_OUT);
      const a = this.seguir(this.lt.T);
      const b = this.ajuste;
      const e = suave(u);
      camara.fijar({ cx: a.cx + (b.cx - a.cx) * e, cy: a.cy + (b.cy - a.cy) * e, w: a.w + (b.w - a.w) * e });
      this.visualFinal();
    }
  }

  /** promedio de las últimas posiciones de la punta: la cámara acompaña sin sacudidas */
  private seguir(t: number): Vista {
    let sx = 0;
    let sy = 0;
    const m = 6;
    for (let j = 0; j < m; j++) {
      const p = this.poly.puntoEn(this.lt.sAt(Math.max(0, t - j * 0.09)));
      sx += p[0];
      sy += p[1];
    }
    const [cx, cy] = this.o.aPantalla(sx / m, sy / m);
    return { cx, cy, w: this.ancho };
  }

  private marcar(i: number): void {
    this.actual = i;
    this.o.alCambiarPaso(i, this.n);
  }

  /** línea punteada en movimiento, marcador de destino con 3 pulsos y góndola resaltada */
  private visualFinal(): void {
    if (this.final) return;
    this.final = true;
    const { linea, base, punta, destino } = this.o.elementos;
    linea.setAttribute("stroke-dasharray", "22 16");
    linea.style.strokeDashoffset = "";
    linea.classList.add("ruta-marcha");
    base.removeAttribute("stroke-dasharray");
    base.style.strokeDashoffset = "";
    punta.style.display = "none";
    destino.style.display = "";
    this.o.resaltar(true);
    destino.classList.remove("destino-pulsa");
    void destino.getBoundingClientRect();
    destino.classList.add("destino-pulsa");
    this.marcar(this.n - 1);
  }

  /** salta al final: ruta completa y vista completa */
  saltar(): void {
    if (this.hecho && this.final) return;
    this.terminar(false);
  }

  private terminar(inmediato: boolean): void {
    cancelAnimationFrame(this.raf);
    this.hecho = true;
    this.visualFinal();
    this.o.camara.irA(this.ajuste, inmediato ? 0 : 350);
  }

  /** muestra el tramo i con la cámara sobre él (el último es la llegada: ruta completa) */
  irPaso(i: number): void {
    const { camara, elementos, aPantalla } = this.o;
    i = Math.max(0, Math.min(this.n - 1, i));
    if (!this.final) {
      cancelAnimationFrame(this.raf);
      this.hecho = true;
      this.visualFinal();
    }
    this.hecho = true;
    this.marcar(i);
    if (i >= this.n - 1) {
      elementos.linea.style.opacity = "";
      elementos.tramo.style.display = "none";
      camara.irA(this.ajuste, 600);
      return;
    }
    const s0 = i > 0 ? this.finales[i - 1] : 0;
    const s1 = this.finales[i];
    const pts: Punto[] = [];
    for (let j = 0; j <= 14; j++) {
      const p = this.poly.puntoEn(s0 + ((s1 - s0) * j) / 14);
      pts.push(aPantalla(p[0], p[1]));
    }
    elementos.tramo.style.display = "";
    elementos.tramo.setAttribute("stroke-dasharray", `${Math.max(1, s1 - s0)} ${this.poly.largo + 10}`);
    elementos.tramo.style.strokeDashoffset = String(-s0);
    elementos.linea.style.opacity = ".45";
    camara.irA(camara.ajustar(pts, 110, Math.max(440, this.ancho * 0.8)), 600);
  }

  /** vuelve a ver la ruta completa */
  verRuta(): void {
    this.saltar();
    const { elementos, camara } = this.o;
    elementos.linea.style.opacity = "";
    elementos.tramo.style.display = "none";
    this.marcar(this.n - 1);
    camara.irA(this.ajuste, 500);
  }

  get terminada(): boolean {
    return this.hecho && this.final;
  }

  destruir(): void {
    this.activo = false;
    cancelAnimationFrame(this.raf);
    this.o.camara.parar();
    if (this.final) this.o.resaltar(false);
  }
}
