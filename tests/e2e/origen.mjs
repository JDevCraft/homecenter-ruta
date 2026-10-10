// Flujo: 1ª búsqueda sin preguntas (sale de la entrada); en la 2ª aparece la ventana «¿Dónde estás?» y la ruta sale de ese pasillo.
// uso: node tests/e2e/origen.mjs [url]   (app corriendo)
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const URL_APP = process.argv[2] ?? "http://localhost:3000";
const SAL = path.resolve("out-e2e");
mkdirSync(SAL, { recursive: true });
const dormir = (ms) => new Promise((r) => setTimeout(r, ms));
const proc = spawn(
  CHROME,
  ["--headless=new", "--disable-gpu", "--remote-debugging-port=9445", `--user-data-dir=${path.resolve(SAL, "perfil2")}`, "about:blank"],
  { stdio: "ignore" },
);
await dormir(2500);
const lista = await (await fetch("http://127.0.0.1:9445/json/list")).json();
const ws = new WebSocket(lista.find((t) => t.type === "page").webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0;
const pend = new Map();
const errores = [];
ws.onmessage = (m) => {
  const d = JSON.parse(m.data);
  if (d.id && pend.has(d.id)) (pend.get(d.id)(d), pend.delete(d.id));
  else if (d.method === "Runtime.exceptionThrown") errores.push(d.params.exceptionDetails.text);
};
const enviar = (method, params = {}) =>
  new Promise((r) => {
    const i = ++id;
    pend.set(i, r);
    ws.send(JSON.stringify({ id: i, method, params }));
  });
const ev = async (expr) =>
  (await enviar("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true })).result.result?.value;
const foto = async (n) =>
  writeFileSync(path.join(SAL, n), Buffer.from((await enviar("Page.captureScreenshot", { format: "png" })).result.data, "base64"));
const escribir = (sel, texto) =>
  ev(
    `(()=>{const i=document.querySelector(${JSON.stringify(sel)});Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(i,${JSON.stringify(texto)});i.dispatchEvent(new Event('input',{bubbles:true}));i.form.requestSubmit()})()`,
  );

await enviar("Page.enable");
await enviar("Runtime.enable");
await enviar("Emulation.setDeviceMetricsOverride", { width: 360, height: 800, deviceScaleFactor: 2, mobile: true });
await enviar("Page.navigate", { url: URL_APP });
await dormir(2500);
const dialogo = () => ev(`document.querySelector('[role=dialog] h2')?.textContent ?? null`);
const linea = () => ev(`document.querySelector('svg [data-r=linea]')?.getAttribute('d')?.slice(0, 24) ?? null`);
const estaAqui = () => ev(`[...document.querySelectorAll('svg text')].filter((t) => t.textContent === 'Estás aquí').length`);
const boton = (texto) =>
  ev(`[...document.querySelectorAll('[role=dialog] button')].find((b) => b.textContent.includes(${JSON.stringify(texto)})).click()`);

await escribir("input[type=search]", "martillo bola");
await dormir(5000);
console.log("1ª búsqueda → ventana:", await dialogo(), "| ruta:", await linea());
await foto("origen_1_entrada.png");

await escribir("input[type=search]", "taladro percutor");
await dormir(1500);
console.log("2ª búsqueda → ventana:", await dialogo(), "| ruta aún sin dibujar:", await linea());
await foto("origen_2_ventana.png");

await escribir("[role=dialog] input", "zzz");
await dormir(300);
console.log("pasillo inválido →", await ev(`document.querySelector('[role=dialog] [role=alert]')?.textContent ?? null`));

await escribir("[role=dialog] input", "05b");
await dormir(5000);
console.log("pasillo 05B → ventana:", await dialogo(), "| ruta:", await linea(), "| «Estás aquí»:", await estaAqui());
await foto("origen_3_desde_05b.png");

await escribir("input[type=search]", "bombillo led");
await dormir(1500);
console.log("3ª búsqueda → ventana:", await dialogo());
await boton("entrada");
await dormir(5000);
console.log("Estoy en la entrada → ruta:", await linea());
console.log("errores:", errores.length ? errores : "ninguno");
ws.close();
proc.kill();
