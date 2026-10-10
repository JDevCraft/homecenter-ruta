"""Genera los datos que usa la app (../data) y los fixtures de las pruebas de paridad (../tests/fixtures) a partir de pipeline/salidas.
Solo se escriben campos públicos del catálogo: SKU, descripción, conjunto, familia y pasillos (el primero con plano es el principal; los demás, alternativas).
No pasan COSTO TOTAL, CANTIDAD, TIPO_INVENTARIO, TIPO REPOSICION ni UBICACION."""
import json, os, sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
os.chdir(RAIZ); sys.path.insert(0, RAIZ)
DATA = os.path.join(RAIZ, "..", "data"); FIX = os.path.join(RAIZ, "..", "tests", "fixtures")
os.makedirs(DATA, exist_ok=True); os.makedirs(FIX, exist_ok=True)

def guardar(ruta, obj, indent=None):
    with open(ruta, "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False, separators=None if indent else (",", ":"), indent=indent)

def copiar(origen, destino):
    guardar(os.path.join(DATA, destino), json.load(open(origen, encoding="utf-8")))

# --- datos del plano, cuadrícula y obstáculos
copiar("salidas/tienda_42.json", "tienda.json")
copiar("salidas/grid_export.json", "grid.json")
copiar("salidas/obstaculos_export.json", "obstaculos.json")
copiar("salidas/categoria_por_pasillo.json", "categorias.json")

# --- catálogo público: tablas de conjunto/familia + filas [sku, descripción, conjunto, familia, [pasillos]]
prods = json.load(open("salidas/catalogo.json", encoding="utf-8"))
conj, fam, ci, fi, filas = [], [], {}, {}, []
for p in prods:
    if p["conjunto"] not in ci: ci[p["conjunto"]] = len(conj); conj.append(p["conjunto"])
    if p["familia"] not in fi: fi[p["familia"]] = len(fam); fam.append(p["familia"])
    pas, vistos = [], set()
    for u in p["ubic"]:
        if u["pasillo"] not in vistos: vistos.add(u["pasillo"]); pas.append(u["pasillo"].upper())
    filas.append([p["sku"], p["desc"], ci[p["conjunto"]], fi[p["familia"]], pas])
guardar(os.path.join(DATA, "catalogo.json"), dict(c=conj, f=fam, p=filas))

# --- geometría que necesita el texto de las instrucciones (misma que usa mapa_cliente.py)
import mapa_cliente as M
guardar(os.path.join(DATA, "instrucciones.json"), dict(
    hitos=[dict(id=h["id"], nombre=h["nombre"], pos=h["pos"], rect=M.HITO_RECT.get(h["id"])) for h in M.HITOS_REF],
    muebles=[dict(v=m["etiquetas"][0], bbox=M.fusionado(m)) for m in M.T["muebles"] if m["tipo"] == "mueble" and m["etiquetas"]],
    fusionados={m["id"]: M.fusionado(m) for m in M.T["muebles"]},
    barreras=[dict(i=b["i"], j=b["j"], lo=b["lo"], hi=b["hi"], span=list(b["span"])) for b in M.BARRERAS_TXT],
    pc=dict(x0=M.PC_X0, y0=M.PC_Y0, x1=M.PC_X1, y1=M.PC_Y1, banda=list(M.PC_BANDA)),
    nombres_hito={"zona-cajas": "los puntos de pago", "rampas": "las rampas eléctricas", "p-exh": "P. EXH", "plataforma": "la plataforma",
                  "asadores": "los asadores", "maquina-pinturas": "la máquina de pinturas", "pisos": "la zona de pisos"}))

# --- fixtures de paridad: lo que calcula Python hoy (rutas, textos y búsquedas)
rd = json.load(open("salidas/rutas_destinos.json", encoding="utf-8"))
rp = json.load(open("salidas/rutas_prueba.json", encoding="utf-8"))
SIN_ANCLA = ["25a:norte", "12c:este", "13c:oeste", "17c:este", "18c:oeste", "06b-N:este", "07b-N:oeste", "15b:este"]
def ref(r, visible):
    mid = r["cara"].split(":")[0]
    m = next(x for x in M.T["muebles"] if x["id"] == mid)
    pasos, fines = M.instrucciones(r, visible, M.fusionado(m), con_fines=True)
    d = M.datos_destino(r, visible)
    return dict(cara=r["cara"], mueble=r["mueble"], alterna=r["cara_alterna"], puntos=r["puntos"], largo=r["largo_pt"], cruza=r["cruza_obstaculo"],
                via=r.get("via"), pasos=pasos, fin=d["fin"], L=d["L"])
fx = dict(destinos={v: ref(r, v) for v, r in rd.items()},
          sin_ancla={k: ref(rp[k], k.split(":")[0]) | dict(pedida=rp[k]["cara_pedida"]) for k in SIN_ANCLA})
guardar(os.path.join(FIX, "rutas_python.json"), fx)

import buscador
idx = buscador.Indice(prods)
CONSULTAS = ["pintura blanco almendra", "pintura", "pintra blanco", "bombillo led", "1/4 galon vinilo", "09715", "9715", "taladro percutor", "xqzzv",
             "inodoro blanco", "cemento gris 50 kg", "martilo", "tornilo", "pinturra azul", "llave", "grifo lavaplatos", "cinta", "nevera", "televisor 50",
             "ducha", "escoba", "guante de trabajo", "caneca", "PINTURA  BLANCA", "óleo", "1 gl", "5 gl pintura azul", "teipe", "foco ahorrador", "zzzz",
             "cable 12", "interruptor doble", "silla", "mesa comedor", "lavadora", "estufa 4 puestos", "tubo pvc 1/2", "manguera jardin", "ladrillo", "a", "de la",
             "pintura blanco almendra vinil", "155139", "40019"]
res = []
for q in CONSULTAS:
    r = idx.buscar(q)
    res.append(dict(q=q, tipo=r["tipo"], skus=[prods[i]["sku"] for i in r["idx"]], sugerencias=r["sugerencias"],
                    resultados=[idx.resultado(i) for i in r["idx"]]))
guardar(os.path.join(FIX, "buscador_python.json"), res)
# --- mapa base para React: el SVG del mapa girado (con colores de familia) como árbol [etiqueta, atributos, hijos]
import xml.etree.ElementTree as ET
svg_txt, (vx, vy, vw, vh) = M.svg_mapa_pagina()
raiz = ET.fromstring(svg_txt)
def nodo(e):
    tag = e.tag.split("}")[-1]
    hijos = ([e.text] if e.text and e.text.strip() else []) + [nodo(h) for h in e]
    return [tag, {k: v for k, v in e.attrib.items() if k != "data-b"}, hijos]
arbol = [nodo(h) for h in raiz if h.attrib.get("id") != "capa-ruta"]
_, cats, _ = M._cargar_familias()
guardar(os.path.join(DATA, "mapa.json"), dict(
    viewBox=[vx, vy, vw, vh], rotm=M.ROTM, F=[M.F["x0"], M.F["y0"], M.FX1, M.F["y1"]],
    ent=dict(x=M.ENT_X, y=M.ENT_Y), origen=M.ORIGEN,
    colores=dict(navy=M.NAVY, azul=M.AZUL, amarillo=M.AMARILLO, rojo=M.ROJO, gondola=M.GONDOLA),
    leyenda=[dict(nombre=n, color=c) for n, c in cats], arbol=arbol))
print("datos:", sorted(os.listdir(DATA)), "| fixtures:", sorted(os.listdir(FIX)))
