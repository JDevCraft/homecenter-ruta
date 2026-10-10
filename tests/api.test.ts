import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";
import { GET, type RespuestaBuscar } from "@/app/api/buscar/route";

const pedir = async (q?: string) => {
  const url = new URL("http://localhost/api/buscar");
  if (q !== undefined) url.searchParams.set("q", q);
  const res = GET(new NextRequest(url));
  return { res, cuerpo: (await res.json()) as RespuestaBuscar };
};

describe("GET /api/buscar", () => {
  it("devuelve 5 resultados con los campos públicos", async () => {
    const { res, cuerpo } = await pedir("pintura blanco almendra");
    expect(res.status).toBe(200);
    expect(cuerpo.resultados).toHaveLength(5);
    expect(cuerpo.resultados[0].sku).toBe("09715");
    expect(Object.keys(cuerpo.resultados[0]).sort()).toEqual(["alternativas", "descripcion", "familia", "idPlano", "pasillo", "sku"]);
    expect(cuerpo.mensaje).toBeNull();
  });
  it("no filtra costos, cantidades, inventario ni reposición", async () => {
    const { cuerpo } = await pedir("taladro percutor");
    expect(JSON.stringify(cuerpo)).not.toMatch(/costo|cantidad|inventario|reposicion|ubicacion/i);
  });
  it("las alternativas dicen si su pasillo está en el plano", async () => {
    const { cuerpo } = await pedir("taladro percutor");
    const con = cuerpo.resultados.find((r) => r.alternativas.length > 0);
    expect(con).toBeDefined();
    for (const a of con?.alternativas ?? []) expect(a.idPlano === null || a.idPlano === a.pasillo.toLowerCase()).toBe(true);
  });
  it("producto fuera del plano: pasillo sin ID de plano, sin error", async () => {
    const { res, cuerpo } = await pedir("40019");
    expect(res.status).toBe(200);
    expect(cuerpo.resultados[0].pasillo).toBe("01D");
    expect(cuerpo.resultados[0].idPlano).toBeNull();
  });
  it("consulta vacía, ausente o de una letra: respuesta clara sin error", async () => {
    for (const q of [undefined, "", "   ", "a"]) {
      const { res, cuerpo } = await pedir(q);
      expect(res.status).toBe(200);
      expect(cuerpo.resultados).toEqual([]);
      expect(cuerpo.mensaje).toMatch(/al menos 2 letras/);
    }
  });
  it("limita la longitud de q", async () => {
    const { res, cuerpo } = await pedir("pintura ".repeat(200));
    expect(res.status).toBe(200);
    expect(cuerpo.q.length).toBeLessThanOrEqual(80);
  });
  it("sin resultados: mensaje y sugerencias", async () => {
    const { cuerpo } = await pedir("xqzzv");
    expect(cuerpo.resultados).toEqual([]);
    expect(cuerpo.mensaje).toMatch(/No encontré/);
    expect(cuerpo.sugerencias).toHaveLength(3);
  });
});
