/** Línea de tiempo de la animación: dibujo a velocidad constante, pausa en cada giro y zoom out final. */

export const PAUSA = 0.3; // s en cada giro
export const ZOOM_OUT = 0.8; // s del zoom out final
const V_MIN = 1.9;
const V_MAX = 2.8;
const VEL = 700; // pt/s; el dibujo dura entre 1,9 y 2,8 s y con las pausas el total queda entre 2,5 y 4 s

export interface Segmento {
  /** tramo (instrucción) que se dibuja en este segmento */
  i: number;
  t0: number;
  t1: number;
  s0: number;
  s1: number;
}

export interface LineaDeTiempo {
  segmentos: Segmento[];
  /** duración del dibujo con las pausas (s) */
  T: number;
  largo: number;
  /** distancia dibujada en el instante t */
  sAt(t: number): number;
  /** tramo activo en el instante t (durante la pausa de un giro ya es el siguiente) */
  tramoAt(t: number): number;
}

/** `finales[i]` = distancia a la que termina el tramo i (el último debe ser el largo total) */
export function crearLineaDeTiempo(largo: number, finales: number[]): LineaDeTiempo {
  const dibujo = Math.min(V_MAX, Math.max(V_MIN, largo / VEL));
  const v = largo / dibujo;
  const segmentos: Segmento[] = [];
  let t = 0;
  finales.forEach((s1, i) => {
    const s0 = i > 0 ? finales[i - 1] : 0;
    const dur = (s1 - s0) / v;
    segmentos.push({ i, t0: t, t1: t + dur, s0, s1 });
    t += dur + (i < finales.length - 1 ? PAUSA : 0);
  });
  return {
    segmentos,
    T: t,
    largo,
    sAt(tt) {
      for (const g of segmentos) {
        if (tt < g.t0) return g.s0;
        if (tt < g.t1) return g.s0 + ((tt - g.t0) * (g.s1 - g.s0)) / (g.t1 - g.t0 || 1);
      }
      return largo;
    },
    tramoAt(tt) {
      for (const g of segmentos) if (tt < g.t1) return g.i;
      return segmentos[segmentos.length - 1].i;
    },
  };
}
