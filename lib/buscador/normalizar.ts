/** Normalización y sinónimos del buscador (port de pipeline/buscador.py: mismas reglas, mismos resultados). */

export const PESO: readonly (readonly [campo: "d" | "c" | "f", peso: number])[] = [
  ["d", 3],
  ["c", 2],
  ["f", 1],
]; // descripción > conjunto > familia

export const STOP = new Set(["de", "del", "la", "el", "los", "las", "y", "para", "con", "en", "un", "una", "por", "al"]);

const ALIAS = new Map<string, string>(
  Object.entries({
    galon: "gl",
    galones: "gl",
    gal: "gl",
    litro: "lt",
    litros: "lt",
    lts: "lt",
    kilo: "kg",
    kilos: "kg",
    kgs: "kg",
    metro: "mt",
    metros: "mt",
    mts: "mt",
    pulgada: "in",
    pulgadas: "in",
    pulg: "in",
    unidad: "und",
    unidades: "und",
    uds: "und",
    cms: "cm",
    mms: "mm",
  }),
);

const SINONIMOS: string[][] = [
  ["bombillo", "bombilla", "foco"],
  ["destornillador", "desarmador"],
  ["inodoro", "sanitario", "taza"],
  ["grifo", "llave"],
  ["lavaplato", "lavadero", "fregadero"],
  ["ducha", "regadera"],
  ["tubo", "tuberia"],
  ["trapero", "mopa"],
  ["clavo", "puntilla"],
  ["cinta", "teipe", "tape"],
  ["nevera", "refrigerador"],
  ["televisor", "tv", "television"],
  ["pintura", "vinilo"],
  ["blanco", "blanca"],
  ["negro", "negra"],
  ["martillo", "mazo"],
  ["candado", "cerrojo"],
  ["cerradura", "chapa"],
  ["pegante", "pegamento", "adhesivo"],
  ["silicona", "silicon"],
  ["ventilador", "abanico"],
  ["lampara", "luminaria"],
  ["interruptor", "switch", "suiche"],
  ["tomacorriente", "toma"],
];

const TOKEN = /\d+(?:[./]\d+)+|[a-z0-9]+/g;
export const tieneDigito = (s: string) => /\d/.test(s);

function normalizar(s: string): string {
  return s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
}

function raiz(t: string): string {
  return t.length > 4 && t.endsWith("s") && !t.endsWith("ss") && !tieneDigito(t) ? t.slice(0, -1) : t;
}

/** palabras de un texto: sin tildes, en minúsculas, con medidas (1/4, 2.5) enteras, abreviaturas unificadas y plural simple */
export function tokens(s: string): string[] {
  return (normalizar(s).match(TOKEN) ?? []).map((t) => raiz(ALIAS.get(t) ?? t));
}

export const SIN = new Map<string, string[]>();
for (const g of SINONIMOS) {
  const gs = g.map(raiz);
  for (const x of gs)
    SIN.set(
      x,
      gs.filter((y) => y !== x),
    );
}

/** distancia de edición con transposición (OSA); corta si supera k */
export function distancia(a: string, b: string, k: number): number {
  if (Math.abs(a.length - b.length) > k) return k + 1;
  let prev2: number[] = [];
  let prev = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    const cur = new Array<number>(b.length + 1).fill(0);
    cur[0] = i;
    for (let j = 1; j <= b.length; j++) {
      const c = a[i - 1] === b[j - 1] ? 0 : 1;
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + c);
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) cur[j] = Math.min(cur[j], prev2[j - 2] + 1);
    }
    if (Math.min(...cur) > k) return k + 1;
    prev2 = prev;
    prev = cur;
  }
  return prev[prev.length - 1];
}
