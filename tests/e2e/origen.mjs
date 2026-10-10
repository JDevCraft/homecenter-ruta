// Flujo «¿en qué pasillo estás?»: 1ª búsqueda desde la entrada, el cliente dice su pasillo, 2ª búsqueda sale de ahí.
// uso: node tests/e2e/origen.mjs [url]   (app corriendo)
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const URL_APP = process.argv[2] ?? "http://localhost:3000";
const SAL = path.resolve("out-e2e");
mkdirSync(SAL, { recursive: true });
const dormir = (ms) => new Promise((r) => setTimeout(r, ms));
const proc = spawn(CHROME, ["--headless=new", "--disable-gpu", "--remote-debugging-port=9445", `--user-data-dir=${path.resolve(SAL, "perfil2")}`, "about:blank"], { stdio: "ignore" });
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
const enviar = (method, params = {}) => new Promise((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => (await enviar("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true })).result.result?.value;
const foto = async (n) => writeFileSync(path.join(SAL, n), Buffer.from((await enviar("Page.captureScreenshot", { format: "png" })).result.data, "base64"));
const escribir = (sel, texto) => ev(`(()=>{const i=document.querySelector(${JSON.stringify(sel)});Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(i,${JSON.stringify(texto)});i.dispatchEvent(new Event('input',{bubbles:true}));i.form.requestSubmit()})()`);

await enviar("Page.enable");
await enviar("Runtime.enable");
await enviar("Emulation.setDeviceMetricsOverride", { width: 360, height: 800, deviceScaleFactor: 2, mobile: true });
await enviar("Page.navigate", { url: URL_APP });
await dormir(2500);
const etiqueta = () => ev(`document.querySelector('form[class*=origen] label')?.textContent ?? null`);
const lineas = () => ev(`[...document.querySelectorAll('svg [data-r=linea]')].map(p=>p.getAttribute('d').slice(0,24))[0] ?? null`);
const estaAqui = () => ev(`[...document.querySelectorAll('svg text')].filter(t=>t.textContent==='Estás aquí').length`);

console.log("antes de buscar, hay campo de pasillo:", await etiqueta());
await escribir("input[type=search]", "martillo bola");
await dormir(5000);
console.log("1ª búsqueda:", await etiqueta(), "| ruta:", await lineas());
await foto("origen_1_entrada.png");

await escribir("#pasillo-actual", "zzz");
await dormir(300);
console.log("pasillo inválido →", await ev(`document.querySelector('form[class*=origen] [role=alert]')?.textContent ?? null`));

await escribir("#pasillo-actual", "05b");
await dormir(300);
console.log("pasillo fijado →", await etiqueta());
await escribir("input[type=search]", "taladro percutor");
await dormir(5000);
console.log("2ª búsqueda:", await lineas(), "| «Estás aquí»:", await estaAqui());
await foto("origen_2_desde_05b.png");

await ev(`[...document.querySelectorAll('form[class*=origen] button')].find(b=>b.textContent==='Entrada').click()`);
await dormir(300);
console.log("volver a entrada →", await etiqueta());
console.log("errores:", errores.length ? errores : "ninguno");
ws.close();
proc.kill();
