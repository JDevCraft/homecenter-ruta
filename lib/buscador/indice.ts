import { PESO, STOP, SIN, distancia, tieneDigito, tokens } from "./normalizar";

export interface Producto {
  sku: string;
  desc: string;
  conjunto: string;
  familia: string;
}

export interface Busqueda {
  /** posiciones en la lista de productos, de mejor a peor */
  idx: number[];
  tipo: "sku" | "todas" | "parcial" | "sin_resultados" | "vacio";
  sugerencias: string[];
}

type Campos = Record<"d" | "c" | "f", string[]>;
type Expansion = Map<string, number>;

const cmpTupla = (a: (string | number)[], b: (string | number)[]) => {
  for (let i = 0; i < a.length; i++) {
    if (a[i] < b[i]) return -1;
    if (a[i] > b[i]) return 1;
  }
  return 0;
};

/** Índice en memoria: se arma una vez (en el servidor) y atiende todas las consultas. */
export class Indice {
  private readonly t: Campos[] = [];
  private readonly vocab = new Map<string, number>();
  private readonly post = new Map<string, number[]>();
  private readonly porLargo = new Map<number, string[]>();
  private readonly inicios = new Map<string, number>();
  private readonly sku = new Map<string, number>();
  private readonly sku0 = new Map<string, number[]>();

  constructor(productos: readonly Producto[]) {
    productos.forEach((pr, i) => {
      const d = tokens(pr.desc);
      const c = tokens(pr.conjunto);
      const f = tokens(pr.familia);
      this.t.push({ d, c, f });
      for (const tk of new Set([...d, ...c, ...f])) {
        this.vocab.set(tk, (this.vocab.get(tk) ?? 0) + 1);
        const p = this.post.get(tk);
        if (p) p.push(i);
        else this.post.set(tk, [i]);
      }
    });
    for (const x of this.t) if (x.d.length > 0 && !tieneDigito(x.d[0])) this.inicios.set(x.d[0], (this.inicios.get(x.d[0]) ?? 0) + 1);
    for (const tk of this.vocab.keys()) {
      const l = this.porLargo.get(tk.length);
      if (l) l.push(tk);
      else this.porLargo.set(tk.length, [tk]);
    }
    productos.forEach((pr, i) => {
      if (!this.sku.has(pr.sku)) this.sku.set(pr.sku, i);
      const z = pr.sku.replace(/^0+/, "");
      const l = this.sku0.get(z);
      if (l) l.push(i);
      else this.sku0.set(z, [i]);
    });
  }

  /** una palabra de la búsqueda → términos del vocabulario con su calidad (exacto 1, sinónimo .9, prefijo .8, error de tipeo .6/.5) */
  private expandir(q: string): Expansion {
    const out: Expansion = new Map();
    const poner = (v: string, w: number) => {
      if (w > (out.get(v) ?? 0)) out.set(v, w);
    };
    if (this.vocab.has(q)) poner(q, 1.0);
    for (const s of SIN.get(q) ?? []) if (this.vocab.has(s)) poner(s, 0.9);
    if (tieneDigito(q)) return out; // medidas y números: solo coincidencia exacta
    if (q.length >= 3) for (const v of this.vocab.keys()) if (v !== q && v.startsWith(q)) poner(v, 0.8);
    if (q.length >= 4) {
      const k = q.length <= 6 ? 1 : 2;
      for (let L = q.length - k; L <= q.length + k; L++) {
        for (const v of this.porLargo.get(L) ?? []) {
          if (v === q || tieneDigito(v)) continue;
          const d = distancia(q, v, k);
          if (d <= k) poner(v, d === 1 ? 0.6 : 0.5);
        }
      }
    }
    return out;
  }

  private puntuar(i: number, exps: Expansion[]): [number, number] {
    const ti = this.t[i];
    const ts: number[] = [];
    const pos: Set<number>[] = [];
    for (const e of exps) {
      let mejor = 0;
      for (const [f, fw] of PESO) {
        let q = 0;
        for (const x of ti[f]) {
          const w = e.get(x) ?? 0;
          if (w > q) q = w;
        }
        if (q * fw > mejor) mejor = q * fw;
      }
      ts.push(mejor);
      const p = new Set<number>();
      ti.d.forEach((x, j) => {
        if ((e.get(x) ?? 0) > 0) p.add(j);
      });
      pos.push(p);
    }
    let bonus = 0;
    for (let a = 0; a + 1 < exps.length; a++) {
      for (const j of pos[a]) {
        if (pos[a + 1].has(j + 1)) {
          bonus += 1.0;
          break;
        }
      }
    }
    if (pos.length > 0 && pos[0].has(0)) bonus += 0.5;
    let suma = 0;
    for (const x of ts) suma += x;
    return [ts.filter((x) => x > 0).length, suma + bonus];
  }

  /** 3 búsquedas parecidas: palabra por palabra, el término más cercano y frecuente del catálogo */
  private sugerir(q: string[], exps: Expansion[], n = 3): string[] {
    const cands: (string | number)[][][] = [];
    q.forEach((x, ix) => {
      const e = exps[ix];
      const c: (string | number)[][] = [];
      if (e.size > 0) {
        let mejor = "";
        let clave: number[] | null = null;
        for (const v of e.keys()) {
          const key = [e.get(v) as number, this.vocab.get(v) as number];
          if (clave === null || cmpTupla(key, clave) > 0) {
            mejor = v;
            clave = key;
          }
        }
        c.push([0, -(this.vocab.get(mejor) as number), mejor]);
      } else {
        for (let L = Math.max(2, x.length - 3); L < x.length + 4; L++) {
          for (const v of this.porLargo.get(L) ?? []) {
            if (tieneDigito(v)) continue;
            const d = distancia(x, v, 2);
            if (d <= 2 || (x.length >= 3 && v.startsWith(x.slice(0, 3)))) c.push([Math.min(d, 4), -(this.vocab.get(v) as number), v]);
          }
        }
      }
      const unicos = [...new Map(c.map((r) => [r.join("\u0001"), r])).values()].sort(cmpTupla);
      cands.push(unicos.slice(0, n));
    });
    const sug: string[] = [];
    const qs = q.join(" ");
    for (let r = 0; r < n; r++) {
      const partes = q.map((x, ix) => (cands[ix].length > 0 ? (cands[ix][Math.min(r, cands[ix].length - 1)][2] as string) : x));
      const s = partes.join(" ");
      if (!sug.includes(s) && s !== qs) sug.push(s);
    }
    if (sug.length === 0) {
      return [...this.inicios.entries()]
        .sort((a, b) => b[1] - a[1])
        .slice(0, 30)
        .filter(([w]) => w.length >= 4)
        .slice(0, n)
        .map(([w]) => w);
    }
    return sug.slice(0, n);
  }

  buscar(texto: string, k = 5): Busqueda {
    const toks = tokens(texto);
    if (toks.length === 1 && /^\d+$/.test(toks[0])) {
      // SKU exacto (con o sin ceros a la izquierda)
      const exacto = this.sku.get(toks[0]);
      if (exacto !== undefined) return { idx: [exacto], tipo: "sku", sugerencias: [] };
      const alt = this.sku0.get(toks[0].replace(/^0+/, "")) ?? [];
      if (alt.length > 0) return { idx: alt.slice(0, k), tipo: "sku", sugerencias: [] };
    }
    let q = toks.filter((x) => !STOP.has(x));
    if (q.length === 0) q = toks;
    q = q.slice(0, 4);
    if (q.length === 0) return { idx: [], tipo: "vacio", sugerencias: [] };
    const exps = q.map((x) => this.expandir(x));
    const cand = new Set<number>();
    for (const e of exps) for (const v of e.keys()) for (const i of this.post.get(v) ?? []) cand.add(i);
    let sc = [...cand].map((i): [number, number, number] => {
      const [m, s] = this.puntuar(i, exps);
      return [i, m, s];
    });
    if (sc.length === 0) return { idx: [], tipo: "sin_resultados", sugerencias: this.sugerir(q, exps) };
    const mx = Math.max(...sc.map((s) => s[1]));
    sc = sc.filter((s) => s[1] === mx);
    sc.sort((a, b) => b[2] - a[2] || this.t[a[0]].d.length - this.t[b[0]].d.length || a[0] - b[0]);
    return { idx: sc.slice(0, k).map((s) => s[0]), tipo: mx === q.length ? "todas" : "parcial", sugerencias: [] };
  }
}
