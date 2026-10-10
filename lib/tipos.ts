/** Punto del plano en puntos del PDF: [x, y] (origen arriba a la izquierda). */
export type Punto = [number, number];
/** Celda de la cuadrícula: [fila, columna]. */
export type Celda = [number, number];
export type Caja = [number, number, number, number];
export type NombreCara = "oeste" | "este" | "norte" | "sur";

interface CaraDato {
  mueble: string;
  cara: NombreCara;
  bbox: Caja;
  visibles: string[];
}

/** data/grid.json, generado por pipeline/ruta.py (RUTA_EXPORTAR). */
export interface GridDato {
  paso: number;
  nx: number;
  ny: number;
  x0: number;
  y0: number;
  margen: number;
  /** bitset en base64, fila por fila; el bit más significativo es la primera celda; 1 = ocupada */
  bits: string;
  origen: Punto;
  celda_origen: Celda;
  banda: Caja | null;
  caras: CaraDato[];
  /** [mueble, cara, fila, columna], en el orden en que se calcularon */
  anclas: [string, NombreCara, number, number][];
  ids: string[];
  vias: { id: string; pos: Punto; celda: Celda; destinos: string[] }[];
}

export interface ObstaculosDato {
  rects: [string, Caja][];
  /** cada polígono es una lista de anillos [exterior, ...huecos] */
  poligonos: number[][][][];
}

export interface RutaOpciones {
  /** cara concreta del mueble (si no tiene paso se usa la contraria) */
  cara?: NombreCara;
  /** pasillo donde está el cliente; si falta, se sale desde la entrada */
  desde?: string | null;
}

export interface Ruta {
  destino: string;
  mueble: string;
  /** "mueble:cara" a la que se llega */
  cara: string;
  caraPedida: NombreCara | null;
  /** true si la cara más cercana a la entrada no tenía paso y se llegó por la contraria */
  ladoContrario: boolean;
  puntos: Punto[];
  /** largo de la polilínea en puntos del plano (solo para comparar; la app no muestra distancias) */
  largo: number;
  /** longitud acumulada donde termina cada tramo; el último valor es la llegada */
  tramos: number[];
  instrucciones: string[];
  /** punto de paso obligado usado (pasillo central), si lo hubo */
  via: Punto | null;
}
