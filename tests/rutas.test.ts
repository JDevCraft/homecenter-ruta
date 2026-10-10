import { describe, expect, it } from "vitest";
import { calcularRuta, cruzaObstaculos, pasillosDelPlano } from "@/lib/ruta";
import { compararTodas } from "./helpers/paridad";

const filas = compararTodas();

describe("paridad de rutas TypeScript vs Python", () => {
  it("cubre los 67 pasillos y las 8 caras sin ancla", () => {
    expect(filas.filter((f) => !f.clave.includes(":"))).toHaveLength(67);
    expect(filas.filter((f) => f.clave.includes(":"))).toHaveLength(8);
  });
  it("misma cara y mismo lado contrario en todas", () => {
    const mal = filas.filter((f) => f.caraPy !== f.caraTs || f.ladoContrarioPy !== f.ladoContrarioTs);
    expect(mal.map((f) => f.clave)).toEqual([]);
  });
  it("el largo difiere menos del 2 %", () => {
    const mal = filas.filter((f) => f.difPct >= 2);
    expect(mal.map((f) => [f.clave, f.difPct])).toEqual([]);
  });
  it("ninguna ruta cruza un obstáculo", () => {
    expect(filas.filter((f) => f.cruzaTs).map((f) => f.clave)).toEqual([]);
  });
  it("los tramos (animación) coinciden con los de Python", () => {
    expect(filas.filter((f) => !f.tramosIguales).map((f) => f.clave)).toEqual([]);
  });
  it("los textos de las indicaciones coinciden con los de Python", () => {
    expect(filas.filter((f) => !f.textosIguales).map((f) => f.clave)).toEqual([]);
  });
});

describe("rutas desde otro pasillo", () => {
  it("de 14c a 13b: llega a 13b, no cruza obstáculos y es corta", () => {
    const r = calcularRuta("13b", { desde: "14c" });
    expect(r.mueble).toBe("13b");
    expect(cruzaObstaculos(r.puntos)).toBe(false);
    expect(r.largo).toBeGreaterThan(0);
    expect(r.largo).toBeLessThan(700);
  });
  it("las 4.422 combinaciones existen y ninguna cruza obstáculos (muestra)", () => {
    const ids = pasillosDelPlano();
    let n = 0;
    for (let i = 0; i < ids.length; i += 1) {
      for (let j = (i * 7) % ids.length; j < ids.length; j += 11) {
        if (ids[i] === ids[j]) continue;
        const r = calcularRuta(ids[j], { desde: ids[i] });
        expect(cruzaObstaculos(r.puntos), `${ids[i]} -> ${ids[j]}`).toBe(false);
        n++;
      }
    }
    expect(n).toBeGreaterThan(200);
  });
  it("destino desconocido lanza error claro", () => {
    expect(() => calcularRuta("zzz")).toThrow(/Sin ruta/);
  });
});
