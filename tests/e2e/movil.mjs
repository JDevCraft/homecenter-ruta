// Prueba en Chrome con emulación móvil (CDP). Requiere la app corriendo: npm run build && npm run start -- -p 3100
// uso: node tests/e2e/movil.mjs [capturas|gif] [url]
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const URL_APP = process.argv[3] ?? "http://localhost:3100";
const MODO = process.argv[2] ?? "capturas";
const SAL = path.resolve("out-e2e");
mkdirSync(SAL, { recursive: true });
const dormir = (ms) => new Promise((r) => setTimeout(r, ms));

const CASOS = [
  ["05b", "75679", "ruta corta"],
  ["39a", "155139", "ruta larga"],
  ["14c", "3090424", "zona c"],
  ["13c", "903637", "lado contrario"],
  ["fuera", "40019", "producto fuera del plano"],
];
const VISTAS = [
  [360, 800],
  [414, 896],
];

const proc = spawn(
  CHROME,
  [
    "--headless=new",
    "--disable-gpu",
    "--remote-debugging-port=9444",
    `--user-data-dir=${path.resolve("out-e2e", "perfil")}`,
    "about:blank",
  ],
  { stdio: "ignore" },
);
await dormir(2500);
const lista = await (await fetch("http://127.0.0.1:9444/json/list")).json();
const ws = new WebSocket(lista.find((t) => t.type === "page").webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0;
const pend = new Map();
const errores = [];
ws.onmessage = (m) => {
  const d = JSON.parse(m.data);
  if (d.id && pend.has(d.id)) {
    pend.get(d.id)(d);
    pend.delete(d.id);
  } else if (d.method === "Runtime.exceptionThrown")
    errores.push(d.params.exceptionDetails.text + " " + (d.params.exceptionDetails.exception?.description ?? ""));
  else if (d.method === "Runtime.consoleAPICalled" && d.params.type === "error")
    errores.push("console.error: " + d.params.args.map((a) => a.value ?? a.description).join(" "));
};
const enviar = (method, params = {}) =>
  new Promise((r) => {
    const i = ++id;
    pend.set(i, r);
    ws.send(JSON.stringify({ id: i, method, params }));
  });
const evaluar = async (expr) =>
  (await enviar("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true })).result.result?.value;
const foto = async (nombre) => {
  const r = await enviar("Page.captureScreenshot", { format: "png" });
  writeFileSync(path.join(SAL, nombre), Buffer.from(r.result.data, "base64"));
};
await enviar("Page.enable");
await enviar("Runtime.enable");

async function buscar(texto) {
  await evaluar(
    `(()=>{const i=document.querySelector('input[type=search]');const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;set.call(i,${JSON.stringify(texto)});i.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('form button[type=submit]').click()})()`,
  );
}

for (const [w, h] of VISTAS) {
  await enviar("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 2, mobile: true });
  await enviar("Emulation.setTouchEmulationEnabled", { enabled: true });
  for (const [nombre, consulta, desc] of CASOS) {
    if (MODO === "gif" && !(["39a", "14c"].includes(nombre) && w === 360)) continue;
    await enviar("Page.navigate", { url: URL_APP });
    await dormir(1800);
    if (MODO === "gif") {
      await foto(`gif_${nombre}_000.png`);
      await buscar(consulta);
      const t0 = Date.now();
      let k = 1;
      while (Date.now() - t0 < 5200) {
        await foto(`gif_${nombre}_${String(k++).padStart(3, "0")}.png`);
      }
      console.log(`GIF ${nombre}: ${k} cuadros`);
      continue;
    }
    await buscar(consulta);
    await dormir(5200);
    await foto(`${w}x${h}_${nombre}.png`);
    const estado = await evaluar(
      `JSON.stringify({paso:document.querySelector('[aria-live=polite]')?.textContent??null,aviso:document.querySelector('[role=status]')?.textContent??null,botones:[...document.querySelectorAll('button')].filter(b=>b.offsetParent).map(b=>Math.round(b.getBoundingClientRect().height)).filter(x=>x<44).length,scrollX:document.documentElement.scrollWidth>window.innerWidth})`,
    );
    console.log(`${w}x${h} ${nombre} (${desc}):`, estado);
  }
}
console.log("errores de consola/excepciones:", errores.length ? errores : "ninguno");
ws.close();
proc.kill();
