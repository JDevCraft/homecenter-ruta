import { describe, expect, it } from "vitest";
import { buscarProductos, productos } from "@/lib/buscador";
import fixtures from "./fixtures/buscador_python.json";

type Fila = { q: string; tipo: string; skus: string[]; sugerencias: string[]; resultados: Record<string, unknown>[] };
const filas = fixtures as unknown as Fila[];

describe("paridad del buscador TypeScript vs Python", () => {
  it.each(filas.map((f) => [f.q, f] as const))("«%s»", (_q, f) => {
    const r = buscarProductos(f.q);
    expect(r.resultados.map((x) => x.sku)).toEqual(f.skus);
    expect(r.tipo).toBe(f.tipo);
    expect(r.sugerencias).toEqual(f.sugerencias);
    // campos que ve el cliente: descripción, familia y pasillo
    expect(r.resultados.map((x) => [x.descripcion, x.familia, x.pasillo, x.idPlano, x.alternativas])).toEqual(
      f.resultados.map((x) => [x.descripcion, x.familia, x.pasillo, x.id_plano, x.alternativas]),
    );
  });
});

describe("casos pedidos", () => {
  it("«pintura blanco almendra» → SKU 09715 primero", () => {
    expect(buscarProductos("pintura blanco almendra").resultados[0].sku).toBe("09715");
  });
  it("el SKU conserva los ceros a la izquierda y se busca con o sin ellos", () => {
    expect(productos.some((p) => p.sku === "09715")).toBe(true);
    expect(buscarProductos("09715").resultados.map((r) => r.sku)).toEqual(["09715"]);
    expect(buscarProductos("9715").resultados[0].sku).toBe("09715");
  });
  it("producto fuera del plano: tiene pasillo pero no ID de plano", () => {
    const r = buscarProductos("40019").resultados[0];
    expect(r.pasillo).toBe("01D");
    expect(r.idPlano).toBeNull();
  });
  it("sin resultados: mensaje y 3 sugerencias", () => {
    const r = buscarProductos("xqzzv");
    expect(r.resultados).toEqual([]);
    expect(r.sugerencias).toHaveLength(3);
  });
  it("devuelve como máximo 5 resultados", () => {
    expect(buscarProductos("pintura").resultados.length).toBeLessThanOrEqual(5);
  });
  it("no filtra campos privados", () => {
    const r = JSON.stringify(buscarProductos("taladro percutor"));
    expect(r).not.toMatch(/costo|cantidad|inventario|reposicion/i);
  });
});
