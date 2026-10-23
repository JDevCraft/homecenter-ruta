/** Línea de tiempo de la animación: dibujo a velocidad constante, pausa en cada giro y zoom out final. */

const PAUSA = 0.5; // s en cada giro: breve, para que el recorrido fluya
export const INTRO_VER = 1.1; // s mostrando la ruta completa y el destino antes de arrancar
export const INTRO_BAJAR = 1.1; // s que tarda la cámara en bajar a la entrada
export const ZOOM_OUT = 0.8; // s del zoom out final
const V_MIN = 6;
const V_MAX = 14;
const VEL = 170; // pt/s; vista previa a ritmo de caminata: el dibujo dura entre 6 y 14 s, más 0,5 s de pausa en cada giro

interface Segmento {
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
