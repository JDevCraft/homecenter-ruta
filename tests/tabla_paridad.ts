import { mkdirSync, writeFileSync } from "node:fs";
import { compararTodas } from "./helpers/paridad";

const f = compararTodas();
const ok = (b: boolean) => (b ? "✓" : "✗");
const linea = (x: (typeof f)[number]) =>
  `| ${x.clave} | ${x.caraPy} | ${x.caraTs} | ${x.ladoContrarioTs ? "sí" : "no"} | ${x.largoPy} | ${x.largoTs} | ${x.difPct.toFixed(2)} % | ${ok(x.puntosIguales)} | ${ok(x.tramosIguales)} | ${ok(x.textosIguales)} | ${x.cruzaTs ? "SÍ" : "no"} |`;
const md = [
  "# Paridad de rutas: TypeScript vs Python",
  "",
  `Pasillos y caras comparados: ${f.length} (67 pasillos + 8 caras sin ancla). Regenerar con \`npm run paridad\`.`,
  "",
  `- Misma cara: ${f.filter((x) => x.caraPy === x.caraTs).length}/${f.length}`,
  `- Mismo lado contrario: ${f.filter((x) => x.ladoContrarioPy === x.ladoContrarioTs).length}/${f.length}`,
  `- Diferencia de largo máxima: ${Math.max(...f.map((x) => x.difPct)).toFixed(2)} % (criterio: menos de 2 %)`,
  `- Puntos idénticos: ${f.filter((x) => x.puntosIguales).length}/${f.length} · tramos idénticos: ${f.filter((x) => x.tramosIguales).length}/${f.length} · textos idénticos: ${f.filter((x) => x.textosIguales).length}/${f.length}`,
  `- Rutas que cruzan un obstáculo: ${f.filter((x) => x.cruzaTs).length}`,
  "",
  "| Destino | Cara Python | Cara TS | Lado contrario | Largo Py (pt) | Largo TS (pt) | Diferencia | Puntos | Tramos | Textos | Cruza |",
  "|---|---|---|---|---|---|---|---|---|---|---|",
  ...f.map(linea),
  "",
].join("\n");
mkdirSync("docs", { recursive: true });
writeFileSync("docs/paridad_rutas.md", md, "utf-8");
console.log(md.split("\n").slice(0, 10).join("\n"));
