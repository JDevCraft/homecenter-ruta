"""Fase 3: clasificación y limpieza -> salidas/tienda_42.json (aplica correcciones.json si existe)."""
import json, os, re, collections

raw = json.load(open("salidas/extraccion_cruda.json", encoding="utf-8"))
FRAME = dict(x0=54.3, y0=224.2, x1=2061.6, y1=1552.5)
cx = lambda r: (r["x0"] + r["x1"]) / 2
cy = lambda r: (r["y0"] + r["y1"]) / 2
inside = lambda r: r["x0"] >= FRAME["x0"] - 1 and r["x1"] <= FRAME["x1"] + 1 and r["y0"] >= FRAME["y0"] - 1 and r["y1"] <= FRAME["y1"] + 1
def c2(c): return None if c is None else tuple(round(v, 2) for v in c)
DARK, GRAY = (0.13, 0.13, 0.13), (0.55, 0.57, 0.58)
FILL = {(0.22, 0.71, 1.0): "punta", (1.0, 0.87, 0.35): "exhibicion", (1.0, 0.46, 0.46): "no_punta"}
MON = {(0.0, 0.09, 0.48): "hogar", (0.77, 0.09, 0.11): "acabados", (0.89, 0.68, 0.24): "especialista",
       (0.89, 0.68, 0.27): "especialista"}
bb = lambda r: [r["x0"], r["y0"], r["x1"], r["y1"]]
ID = re.compile(r"^\d{2}[abc]$")

rects = [r for r in raw["rects"] if inside(r) and r["w"] < 1500]
words = [w for w in raw["words"] if inside(w)]
dentro = [r for r in raw["rects"] if inside(r)]
print("rects dentro", len(dentro), "fuera", len(raw["rects"]) - len(dentro))

dark = [r for r in rects if c2(r["stroke"]) == DARK and not r["fill"]]
gray = [r for r in rects if c2(r["stroke"]) == GRAY and not r["fill"]]
fills = [r for r in rects if r["fill"] and c2(r["fill"]) in FILL]
mons = [r for r in rects if (r["stroke"] and c2(r["stroke"]) in MON) or (r["fill"] and c2(r["fill"]) in MON)]
rest = [r for r in rects if r not in dark and r not in gray and r not in fills and r not in mons]
print("oscuros", len(dark), "grises", len(gray), "rellenos", len(fills), "monetizado", len(mons), "otros", len(rest))

muebles = [dict(id=None, id_visible=None, etiquetas=[], tipo="mueble", bbox=bb(r), atributos={}) for r in dark]

def dist(b, r):
    dx = max(b[0] - r["x1"], r["x0"] - b[2], 0); dy = max(b[1] - r["y1"], r["y0"] - b[3], 0)
    return (dx * dx + dy * dy) ** .5
def nearest(r, maxd=6):
    m = min(muebles, key=lambda m: dist(m["bbox"], r))
    return m if dist(m["bbox"], r) <= maxd else None

huerfanos = []
for r in fills:
    m = nearest(r)
    item = dict(tipo=FILL[c2(r["fill"])], bbox=bb(r))
    if m: m["atributos"].setdefault("puntas", []).append(item)
    else: huerfanos.append(dict(item, motivo="relleno sin mueble adyacente"))
for r in mons:
    m = nearest(r, 12)
    c = c2(r["stroke"]) if r["stroke"] and c2(r["stroke"]) in MON else c2(r["fill"])
    item = dict(categoria=MON[c], forma="mueble" if r["stroke"] else "punta", bbox=bb(r))
    if m: m["atributos"].setdefault("comercial", []).append(item)
    else: huerfanos.append(dict(item, motivo="marca monetizada sin mueble"))
for w in words:
    if w["text"] in ("PG", "PRS", "PRSW", "PRH"):
        for m in muebles:
            for p in m["atributos"].get("puntas", []):
                b = p["bbox"]
                if b[0] <= cx(w) <= b[2] and b[1] <= cy(w) <= b[3]: p["codigo"] = w["text"]

# etiquetas -> rectángulo oscuro que las contiene
sin_mueble = []
for w in words:
    if not ID.match(w["text"]): continue
    c = [m for m in muebles if m["bbox"][0] <= cx(w) <= m["bbox"][2] and m["bbox"][1] <= cy(w) <= m["bbox"][3]]
    if not c: sin_mueble.append(w["text"]); continue
    m = min(c, key=lambda m: (m["bbox"][2]-m["bbox"][0]) * (m["bbox"][3]-m["bbox"][1]))
    if w["text"] not in m["etiquetas"]: m["etiquetas"].append(w["text"])
    m.setdefault("_ys", []).append(cy(w))

# hitos por texto
HITOS = {"P.": ("p-exh", "P. EXH"), "PUNTOS": ("zona-cajas", "Puntos de pago"), "RAMPAS": ("rampas", "Rampas eléctricas"),
         "Plataforma": ("plataforma", "Plataforma"), "Asadores": ("asadores", "Asadores"),
         "pinturas": ("maquina-pinturas", "Máquina de pinturas"), "PISOS": ("pisos", "Pisos"),
         "Cables": ("maquina-cables", "Máquina de cables"), "ENTRADA": ("acceso-principal", "Entrada // Salida")}
hitos = []
for w in words:
    if w["text"] in HITOS:
        hid, nom = HITOS[w["text"]]
        m = next((m for m in muebles if m["bbox"][0] <= cx(w) <= m["bbox"][2] and m["bbox"][1] <= cy(w) <= m["bbox"][3]), None)
        hitos.append(dict(id=hid, nombre=nom, pos=[round(cx(w), 1), round(cy(w), 1)], mueble=None))
        if m and not m["etiquetas"]: m["hito"] = hid
        if m and hid == "plataforma": m["hito"] = hid
        hitos[-1]["_m"] = m

# IDs: tramos partidos N/S
grp = collections.defaultdict(list)
for m in muebles:
    for e in m["etiquetas"]: grp[e].append(m)
notas = []
for e, ms in grp.items():
    if len(ms) == 2 and e[2] == "b":
        ms.sort(key=lambda m: m["bbox"][1])
        for m, s in zip(ms, "NS"): m.setdefault("_split", {})[e] = f"{e}-{s}"
    elif len(ms) == 1 and e[2] == "b" and len([1 for _ in ms[0]["_ys"]]) > 1 and ms[0]["_ys"].count(0) == 0:
        pass
for m in muebles:
    et = m["etiquetas"]
    if m.get("hito") == "plataforma" or len(et) > 1:
        m["id"] = m.get("hito") or "+".join(et); m["id_visible"] = et
        m["tipo"] = "hito"; continue
    if len(et) == 1:
        e = et[0]
        m["id"] = m.get("_split", {}).get(e, e); m["id_visible"] = e
        if m["_ys"].__len__() > 1 and e not in m.get("_split", {}):
            notas.append(f"{e}: 2 palabras dentro de un mismo rectángulo (tramo N y S unidos o etiqueta repetida)")
    elif m.get("hito"):
        m["id"] = m["hito"]; m["id_visible"] = None; m["tipo"] = "hito"
    else:
        m["tipo"] = "sin_clasificar"
# reglas geométricas sobre los oscuros sin etiqueta (no se adivina: lo que no cumple queda sin clasificar)
R = lambda m: dict(x0=m["bbox"][0], y0=m["bbox"][1], x1=m["bbox"][2], y1=m["bbox"][3])
def vsolape(a, b):
    o = min(a[3], b[3]) - max(a[1], b[1]); return o / max(1, min(a[3]-a[1], b[3]-b[1]))
con_id = [m for m in muebles if m["tipo"] != "sin_clasificar"]
sin_id = [m for m in muebles if m["tipo"] == "sin_clasificar"]
# A) cabecera: oscuro de ~20-26 de lado corto que toca el extremo de un mueble con ID
for m in sin_id:
    w, h = m["bbox"][2]-m["bbox"][0], m["bbox"][3]-m["bbox"][1]
    if min(w, h) <= 30:
        cand = [(dist(c["bbox"], R(m)), c) for c in con_id if c["tipo"] == "mueble" and dist(c["bbox"], R(m)) <= 6]
        # hasta 30 de lado corto solo si coincide con una punta rellena del mueble vecino (DIVA de 35a)
        if min(w, h) > 26:
            cand = [(d, c) for d, c in cand if any(all(abs(p["bbox"][i] - m["bbox"][i]) <= 2 for i in range(4)) for p in c["atributos"].get("puntas", []))]
        if cand:
            d, c = min(cand, key=lambda t: t[0])
            c["atributos"].setdefault("cabeceras", []).append(dict(bbox=m["bbox"], puntas=m["atributos"].get("puntas", [])))
            m["tipo"] = "cabecera"; m["id"] = c["id"] + ":cabecera"; m["cabecera_de"] = c["id"]
# B) continuación de fila: sin texto, a la derecha de un mueble con ID y en su misma fila
for m in [x for x in muebles if x["tipo"] == "sin_clasificar"]:
    c = [c for c in con_id if c["tipo"] == "mueble" and c["bbox"][2] <= m["bbox"][0] + 2 and vsolape(c["bbox"], m["bbox"]) >= .7
         and m["bbox"][0] - c["bbox"][2] <= 60
         and (m["bbox"][2]-m["bbox"][0]) >= 3 * (m["bbox"][3]-m["bbox"][1])]  # solo barras horizontales (filas 28a-45a)
    if c:
        c = max(c, key=lambda c: c["bbox"][2])
        m["tipo"] = "continuacion"; m["id"] = c["id"] + "-E"; m["continuacion_de"] = c["id"]
sc = [m for m in muebles if m["tipo"] == "sin_clasificar"]
for i, m in enumerate(sorted(sc, key=lambda m: (m["bbox"][0], m["bbox"][1])), 1): m["id"] = f"sc-{i:02d}"
for m in muebles: m.pop("_ys", None); m.pop("_split", None); m.pop("hito", None)

# módulos pequeños grises -> bloques contiguos
modmon = [r for r in mons if r['stroke'] and r['w'] < 40 and r['h'] < 40]
mods = [bb(r) for r in gray + modmon]
par = list(range(len(mods)))
def f(i):
    while par[i] != i: par[i] = par[par[i]]; i = par[i]
    return i
for i in range(len(mods)):
    for j in range(i):
        if dist(mods[i], dict(x0=mods[j][0], y0=mods[j][1], x1=mods[j][2], y1=mods[j][3])) <= 3: par[f(i)] = f(j)
bl = collections.defaultdict(list)
for i, b in enumerate(mods): bl[f(i)].append(b)
bloques = []
for k, bs in enumerate(sorted(bl.values(), key=lambda bs: (min(b[0] for b in bs), min(b[1] for b in bs))), 1):
    bloques.append(dict(id=f"bloque-{k:02d}", n=len(bs), bbox=[min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)], modulos=bs))

# marcas monetizadas huérfanas -> bloque de módulos que las contiene/toca
quedan = []
for h in huerfanos:
    bk = min(bloques, key=lambda k: dist(k["bbox"], dict(x0=h["bbox"][0], y0=h["bbox"][1], x1=h["bbox"][2], y1=h["bbox"][3])))
    if "categoria" in h and dist(bk["bbox"], dict(x0=h["bbox"][0], y0=h["bbox"][1], x1=h["bbox"][2], y1=h["bbox"][3])) <= 6:
        bk.setdefault("comercial", []).append(dict(categoria=h["categoria"], forma=h["forma"], bbox=h["bbox"]))
    else: quedan.append(h)
huerfanos = quedan
postes = [r for r in rest if r["w"] < 12 and r["h"] < 12]  # dos postes junto a la entrada
rest = [r for r in rest if r not in postes]

extra = []  # obstáculos que el PDF no trae como rect/línea (se agregan solo desde correcciones.json)
if os.path.exists("correcciones.json"):
    for c in json.load(open("correcciones.json", encoding="utf-8")):
        if c.get("accion") == "agregar_obstaculo":
            extra.append(dict(id=c["id"], bbox=c["bbox"], motivo=c.get("motivo", ""))); continue
        for m in muebles:
            if m["id"] == c["id"]: m.update(c.get("set", {}))

for h in hitos: h.pop("_m")
cat = collections.Counter()
for m in muebles: cat["oscuro:" + m["tipo"]] += 1
cat["modulo_gris"] = len(gray); cat["relleno_punta"] = len(fills); cat["marca_monetizada"] = len(mons)
cat["postes"] = len(postes); cat["otros"] = len(rest)
total = sum(cat.values()); assert total == len(dentro), (total, len(dentro))
assert len(set(map(id, dark + gray + fills + mons + postes + rest))) == len(dentro), "rectángulo en 2 categorías o ninguna"
print("reconciliación:", dict(cat), "=", total, "+ fuera", len(raw["rects"]) - len(dentro), "=", len(raw["rects"]))
ids = sorted({e for m in muebles for e in m["etiquetas"]})
out = dict(tienda=dict(id="tienda-42", marco=FRAME, unidad="pt", direccion="Av. Carrera 68 # 80-77, Bogotá"), muebles=muebles,
           bloques_modulos=bloques, hitos=hitos, huerfanos=huerfanos, otros_rectangulos=[bb(r) for r in rest],
           postes_entrada=[bb(r) for r in postes], obstaculos_extra=extra,
           accesos=[dict(id="acceso-principal", nombre="Entrada // Salida",
                         # punto medio entre los 2 postes, ~18 pt hacia el interior (sur)
                         pos=[round(sum((r["x0"] + r["x1"]) / 2 for r in postes) / len(postes), 1),
                              round(sum((r["y0"] + r["y1"]) / 2 for r in postes) / len(postes) + 18, 1)])], notas=notas, etiquetas_sin_mueble=sin_mueble)
json.dump(out, open("salidas/tienda_42.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("muebles", len(muebles), "| sin_clasificar", len(sc), "| bloques", len(bloques), "| IDs únicos", len(ids),
      "| huérfanos", len(huerfanos), "| otros", len(rest), "| etiq sin mueble", sin_mueble)
print("notas", notas)
