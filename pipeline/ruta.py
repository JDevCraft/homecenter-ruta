"""Fase 5: zona caminable, anclas por cara, conectividad, A* + suavizado, rutas de prueba.
Uso: python -I scripts/ruta.py [margen_pt|barrido] [celda_pt]
Sin margen (o "barrido"): prueba varios y elige el mayor que conecta los 67 IDs."""
import json, sys, os, heapq, math, collections
import numpy as np, pymupdf
from shapely.geometry import box, LineString
from shapely.ops import unary_union
import shapely

T = json.load(open("salidas/tienda_42.json", encoding="utf-8"))
F = T["tienda"]["marco"]
OUT = os.environ.get("RUTA_OUT", "salidas"); os.makedirs(OUT, exist_ok=True)  # la POC no calcula metros ni distancias
STEP = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
ORIGEN = T["accesos"][0]["pos"]
NX = int(math.ceil((F["x1"] - F["x0"]) / STEP)); NY = int(math.ceil((F["y1"] - F["y0"]) / STEP))
cxs = F["x0"] + (np.arange(NX) + .5) * STEP; cys = F["y0"] + (np.arange(NY) + .5) * STEP
GX, GY = np.meshgrid(cxs, cys)

# 1-2) obstáculos: muebles (cabeceras y continuaciones incluidas = fusión con su mueble), módulos, postes
OBS = [(m["id"], m["bbox"]) for m in T["muebles"]]
OBS += [("poste", p) for p in T["postes_entrada"]]
OBS += [(o["id"], o["bbox"]) for o in T.get("obstaculos_extra", [])]  # vienen de correcciones.json
# módulos grises: los huecos entre módulos contiguos (~13-16 pt) son separaciones del dibujo, no pasos.
# Cierre morfológico: buffer +CIERRE, unión, buffer -CIERRE -> cada fila/columna queda como una sola barrera.
CIERRE = 10
CORR = json.load(open("correcciones.json", encoding="utf-8")) if os.path.exists("correcciones.json") else []
# regiones con cierre propio (p. ej. columna derecha: cierre 0 = cada módulo es un obstáculo individual)
VIAS = [] if os.environ.get("RUTA_SIN_VIA") else [c for c in CORR if c.get("accion") == "ruta_via"]
SIN_REG = set(os.environ.get("RUTA_SIN_REGION", "").split(","))  # ids de región a ignorar (para comparar antes/después)
REGIONES = [] if os.environ.get("RUTA_SIN_EXCEPCION") else [c for c in CORR if c.get("accion") == "cierre_modulos" and c["id"] not in SIN_REG]
MODS = [box(*mo) for b in T["bloques_modulos"] for mo in b["modulos"]]
def region_de(g):
    cx, cy = g.centroid.x, g.centroid.y
    for r in REGIONES:
        x0, y0, x1, y1 = r["region"]
        if x0 <= cx <= x1 and y0 <= cy <= y1: return r["id"]
    return None
def cerrar(gs, c):
    if c <= 0: return list(gs)
    return list(unary_union([g.buffer(c, join_style=2) for g in gs]).buffer(-c, join_style=2).geoms)
BARRERAS = cerrar([g for g in MODS if region_de(g) is None], CIERRE)
for r in REGIONES:
    if r.get("transitable"): continue  # pasillo central: los módulos no son obstáculo
    BARRERAS += cerrar([g for g in MODS if region_de(g) == r["id"]], r.get("cierre", CIERRE))
TRANS = [r for r in REGIONES if r.get("transitable")]
BANDA_C = None  # pasillo central: banda de la fila de módulos transitable
if TRANS:
    _b = [g.bounds for g in MODS if region_de(g) == TRANS[0]["id"]]
    BANDA_C = (min(b[0] for b in _b), min(b[1] for b in _b), max(b[2] for b in _b), max(b[3] for b in _b))

def centrar_pasillo(pts):
    """los vértices que quedan pegados a las cabeceras dentro del pasillo central pasan al eje de la banda"""
    if not BANDA_C: return pts
    yc = (BANDA_C[1] + BANDA_C[3]) / 2
    return [(x, yc) if (BANDA_C[0] - 60 <= x <= BANDA_C[2] + 60 and BANDA_C[1] + 15 <= y <= BANDA_C[3] + 4 and 0 < i < len(pts) - 1) else (x, y)
            for i, (x, y) in enumerate(pts)]

BARRERAS_INT = [g.buffer(-.5, join_style=2) for g in BARRERAS]


def mask(margen):
    blk = (GX < F["x0"] + margen) | (GX > F["x1"] - margen) | (GY < F["y0"] + margen) | (GY > F["y1"] - margen)
    for _, b in OBS:
        blk |= (GX >= b[0] - margen) & (GX <= b[2] + margen) & (GY >= b[1] - margen) & (GY <= b[3] + margen)
    for g in BARRERAS:
        x0, y0, x1, y1 = g.bounds; x0 -= margen; y0 -= margen; x1 += margen; y1 += margen
        sub = (GX >= x0) & (GX <= x1) & (GY >= y0) & (GY <= y1)
        ys, xs = np.nonzero(sub)
        ok = shapely.contains_xy(g.buffer(margen, join_style=2), GX[ys, xs], GY[ys, xs]) | shapely.touches(g.buffer(margen, join_style=2), shapely.points(GX[ys, xs], GY[ys, xs]))
        blk[ys[ok], xs[ok]] = True
    return blk


cell = lambda p: (int((p[1] - F["y0"]) / STEP), int((p[0] - F["x0"]) / STEP))
ctr = lambda c: (F["x0"] + (c[1] + .5) * STEP, F["y0"] + (c[0] + .5) * STEP)
N8 = [(-1, 0, 1), (1, 0, 1), (0, -1, 1), (0, 1, 1), (-1, -1, 1.4142), (-1, 1, 1.4142), (1, -1, 1.4142), (1, 1, 1.4142)]


def libre_cercana(blk, p, r=8):
    c = cell(p)
    for d in range(r + 1):
        for dy in range(-d, d + 1):
            for dx in range(-d, d + 1):
                y, x = c[0] + dy, c[1] + dx
                if 0 <= y < NY and 0 <= x < NX and not blk[y, x]:
                    return (y, x)
    return None


def bfs(blk, s):
    seen = np.zeros((NY, NX), dtype=bool); seen[s] = True; q = collections.deque([s])
    while q:
        y, x = q.popleft()
        for dy, dx, _ in N8:
            ny, nx = y + dy, x + dx
            if 0 <= ny < NY and 0 <= nx < NX and not seen[ny, nx] and not blk[ny, nx]:
                if dy and dx and (blk[y + dy, x] or blk[y, x + dx]):
                    continue
                seen[ny, nx] = True; q.append((ny, nx))
    return seen


def cruza(poly, propios=()):
    """True si algún punto de la polilínea cae dentro de un obstáculo (sin inflar): rectángulos y barreras de módulos."""
    ls = LineString(poly)
    if any(ls.intersects(g) for g in BARRERAS_INT):
        return True
    for (x0, y0), (x1, y1) in zip(poly, poly[1:]):
        n = max(2, int(math.hypot(x1 - x0, y1 - y0)))
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n; y = y0 + (y1 - y0) * i / n
            for nm, b in OBS:
                if nm in propios:
                    continue
                if b[0] + .5 < x < b[2] - .5 and b[1] + .5 < y < b[3] - .5:
                    return True
    return False


# 5) anclas por cara: muebles con ID (bbox fusionado con sus cabeceras), lados largos
def caras():
    out = []
    for m in T["muebles"]:
        if m["tipo"] not in ("mueble", "hito") or not (m["etiquetas"] or m["tipo"] == "hito"):
            continue
        b = list(m["bbox"])
        for c in m["atributos"].get("cabeceras", []):
            b = [min(b[0], c["bbox"][0]), min(b[1], c["bbox"][1]), max(b[2], c["bbox"][2]), max(b[3], c["bbox"][3])]
        w, h = b[2] - b[0], b[3] - b[1]
        lados = ["oeste", "este"] if h >= 1.5 * w else ["norte", "sur"] if w >= 1.5 * h else ["oeste", "este", "norte", "sur"]
        for l in lados:
            out.append(dict(mueble=m["id"], cara=l, bbox=b, visibles=m["etiquetas"] or [m["id"]]))
    return out


CARAS = caras()
# los propios de una cara: el mueble y sus cabeceras (no cuentan como obstáculo entre ancla y cara)
PROPIOS = {m["id"]: {m["id"]} | {x["id"] for x in T["muebles"] if x.get("cabecera_de") == m["id"]} for m in T["muebles"]}


def anclar(cara, reach, margen):
    b = cara["bbox"]; l = cara["cara"]; d = margen + STEP
    sel = reach.copy()
    if l == "oeste": sel &= (GX <= b[0] - margen + 1) & (GX >= b[0] - 40) & (GY >= b[1]) & (GY <= b[3])
    if l == "este": sel &= (GX >= b[2] + margen - 1) & (GX <= b[2] + 40) & (GY >= b[1]) & (GY <= b[3])
    if l == "norte": sel &= (GY <= b[1] - margen + 1) & (GY >= b[1] - 40) & (GX >= b[0]) & (GX <= b[2])
    if l == "sur": sel &= (GY >= b[3] + margen - 1) & (GY <= b[3] + 40) & (GX >= b[0]) & (GX <= b[2])
    ys, xs = np.nonzero(sel)
    if not len(ys):
        return None
    mx, my = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    ix, iy = {"oeste": (b[0] - d, my), "este": (b[2] + d, my), "norte": (mx, b[1] - d), "sur": (mx, b[3] + d)}[l]
    o = np.argsort((GX[ys, xs] - ix) ** 2 + (GY[ys, xs] - iy) ** 2)
    for k in o[:60]:  # visible desde la cara sin atravesar otro mueble
        p = (GX[ys[k], xs[k]], GY[ys[k], xs[k]])
        q = (min(max(p[0], b[0]), b[2]), min(max(p[1], b[1]), b[3]))
        if not cruza([p, q], PROPIOS[cara["mueble"]]):
            return (int(ys[k]), int(xs[k]))
    return None


def evaluar(margen):
    blk = mask(margen); s = libre_cercana(blk, ORIGEN)
    if s is None:
        return blk, None, {}, {}
    reach = bfs(blk, s); anc = {}
    for c in CARAS:
        a = anclar(c, reach, margen)
        if a is not None:
            anc[(c["mueble"], c["cara"])] = a
    ids = collections.defaultdict(list)
    for c in CARAS:
        for v in c["visibles"]:
            if (c["mueble"], c["cara"]) in anc:
                ids[v].append((c["mueble"], c["cara"]))
    return blk, reach, anc, ids


todos = sorted({v for c in CARAS for v in c["visibles"] if len(v) == 3 and v[:2].isdigit()})
if len(sys.argv) > 1 and sys.argv[1] != "barrido":
    margenes = [float(sys.argv[1])]
else:
    margenes = [10, 8, 7, 6, 5, 4, 3, 2, 0]
elegido = None
print(f"celda {STEP} pt | origen {ORIGEN} | IDs a alcanzar: {len(todos)}")
for m in margenes:
    blk, reach, anc, ids = evaluar(m)
    falt = [v for v in todos if v not in ids]
    print(f"margen {m:>4}: libres {int((~blk).sum()):>6} | alcanzables {0 if reach is None else int(reach.sum()):>6} | IDs alcanzados {len(todos) - len(falt)}/{len(todos)}")
    if elegido is None and not falt:
        elegido = (m, blk, reach, anc, ids)
if elegido is None:
    m = margenes[-1]; blk, reach, anc, ids = evaluar(m); elegido = (m, blk, reach, anc, ids)
margen, blk, reach, anc, ids = elegido
falt = [v for v in todos if v not in ids]
json.dump(dict(margen=margen, celda=STEP, origen=ORIGEN, ids_no_alcanzados=falt,
               caras_sin_ancla=[f"{c['mueble']}:{c['cara']}" for c in CARAS if (c["mueble"], c["cara"]) not in anc],
               anclas={f"{k[0]}:{k[1]}": [round(v, 1) for v in ctr(a)] for k, a in anc.items()}),
          open(f"{OUT}/conectividad.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("margen elegido", margen, "| no alcanzados:", falt)
print("caras sin ancla:", [f"{c['mueble']}:{c['cara']}" for c in CARAS if (c["mueble"], c["cara"]) not in anc])


# 6) A* + suavizado por línea de vista
def astar(blk, s, metas):
    metas = set(metas); gy = list(metas)
    h = lambda c: min(math.hypot(c[0] - g[0], c[1] - g[1]) for g in gy)
    pq = [(h(s), 0, s)]; g = {s: 0}; pa = {}
    while pq:
        _, gc, c = heapq.heappop(pq)
        if c in metas:
            r = [c]
            while c in pa:
                c = pa[c]; r.append(c)
            return r[::-1]
        if gc > g[c]:
            continue
        for dy, dx, w in N8:
            n = (c[0] + dy, c[1] + dx)
            if not (0 <= n[0] < NY and 0 <= n[1] < NX) or blk[n]:
                continue
            if dy and dx and (blk[c[0] + dy, c[1]] or blk[c[0], c[1] + dx]):
                continue
            ng = gc + w
            if ng < g.get(n, 1e18):
                g[n] = ng; pa[n] = c; heapq.heappush(pq, (ng + h(n), ng, n))
    return None


def los(blk, a, b):
    n = int(max(abs(a[0] - b[0]), abs(a[1] - b[1])) * 2) + 1
    for i in range(n + 1):
        y = a[0] + (b[0] - a[0]) * i / n; x = a[1] + (b[1] - a[1]) * i / n
        if blk[int(round(y)), int(round(x))] or blk[int(y), int(round(x))] or blk[int(round(y)), int(x)]:
            return False
    return True


def suavizar(blk, camino):
    r = [camino[0]]; i = 0
    while i < len(camino) - 1:
        j = len(camino) - 1
        while j > i + 1 and not los(blk, camino[i], camino[j]):
            j -= 1
        r.append(camino[j]); i = j
    return r


def referencia(p):
    mejor = None
    for h in T["hitos"]:
        if h["id"] == "acceso-principal":
            continue
        d = math.hypot(h["pos"][0] - p[0], h["pos"][1] - p[1])
        if d < 160 and (mejor is None or d < mejor[0]):
            mejor = (d, h["nombre"])
    if mejor:
        return mejor[1]
    d, m = min((math.hypot((mm["bbox"][0] + mm["bbox"][2]) / 2 - p[0], (mm["bbox"][1] + mm["bbox"][3]) / 2 - p[1]), mm)
               for mm in T["muebles"] if mm["tipo"] == "mueble" and mm["etiquetas"])
    return "pasillo " + m["etiquetas"][0]


def instrucciones(pts, destino):
    txt = ["Estás en la entrada."]
    for i in range(1, len(pts) - 1):
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        d1 = (b[0] - a[0], b[1] - a[1]); d2 = (c[0] - b[0], c[1] - b[1])
        ang = math.degrees(math.atan2(d1[0] * d2[1] - d1[1] * d2[0], d1[0] * d2[0] + d1[1] * d2[1]))
        if abs(ang) < 30:
            continue
        txt.append(f"Gira a la {'derecha' if ang > 0 else 'izquierda'} a la altura de {referencia(b)}.")
    txt.append(f"Llegaste: {destino}.")
    return txt


largo = lambda pts: sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
bg = pymupdf.open("fuentes/Calle 80 con puntas 2.pdf")[0].get_pixmap(matrix=pymupdf.Matrix(1.2, 1.2))


def dibujar(nombre, pts, dest_pt, objetivo):
    doc = pymupdf.open(); pg = doc.new_page(width=2126.25, height=1701)
    pg.insert_image(pg.rect, pixmap=bg)
    for _, b in OBS:
        pg.draw_rect(pymupdf.Rect(*b), color=(.6, .65, .75), width=1)
    for g in BARRERAS:
        pg.draw_polyline(list(g.exterior.coords), color=(.9, .45, .1), width=1.5, closePath=True)
    for a, b in zip(pts, pts[1:]):
        pg.draw_line(a, b, color=(.016, .118, .494), width=7, dashes="[14 10] 0")
    pg.draw_circle(pts[0], 14, color=(.016, .118, .494), fill=(.016, .118, .494))
    pg.draw_circle(dest_pt, 14, color=(.95, .78, .01), fill=(.95, .78, .01))
    pg.insert_text((dest_pt[0] + 18, dest_pt[1] - 8), objetivo, fontsize=26, color=(.07, .14, .23))
    pg.get_pixmap(matrix=pymupdf.Matrix(.8, .8)).save(f"{OUT}/ruta_{nombre}.png")


COLUMNA = ["29a", "30a", "31a", "32a", "33a", "34a", "35a", "36a", "37a", "38a", "39a"]
SIN_ANCLA = ["25a:norte", "12c:este", "13c:oeste", "17c:este", "18c:oeste", "06b-N:este", "07b-N:oeste", "15b:este"]
OPUESTA = {"oeste": "este", "este": "oeste", "norte": "sur", "sur": "norte"}
FILA_C = ["05c", "07c", "08c", "09c"] + [f"{n}c" for n in range(10, 22)]
CASOS = ["05b", "21a", "14c", "12b-S"] + COLUMNA + [c for c in FILA_C if c != "14c"] + SIN_ANCLA
s = libre_cercana(blk, ORIGEN); resultados = {}
print("\n--- rutas de prueba ---")
# --- modo RUTA_EXPORTAR: datos que usa la app (TypeScript) en vez de recalcular nada en el navegador ---
# cuadrícula de ocupación (bitset), anclas por cara, puntos de paso, banda del pasillo central y geometría de obstáculos para las pruebas
if os.environ.get("RUTA_EXPORTAR"):
    import base64
    bits = base64.b64encode(np.packbits(blk.astype(np.uint8).ravel()).tobytes()).decode()   # bit más significativo = primera celda
    def anillos(g):
        polys = [g] if g.geom_type == "Polygon" else list(getattr(g, "geoms", []))
        return [[[round(x, 2), round(y, 2)] for x, y in [p.exterior.coords[i] for i in range(len(p.exterior.coords))]] for p in polys if not p.is_empty] + \
               [[[round(x, 2), round(y, 2)] for x, y in r.coords] for p in polys if not p.is_empty for r in p.interiors]
    grid = dict(paso=STEP, nx=NX, ny=NY, x0=F["x0"], y0=F["y0"], margen=margen, bits=bits,
                origen=list(ORIGEN), celda_origen=list(libre_cercana(blk, ORIGEN)),
                banda=list(BANDA_C) if BANDA_C else None,
                caras=[dict(mueble=c["mueble"], cara=c["cara"], bbox=c["bbox"], visibles=c["visibles"]) for c in CARAS],
                anclas=[[k[0], k[1], int(v[0]), int(v[1])] for k, v in anc.items()],
                ids=todos,
                vias=[dict(id=v["id"], pos=v["pos"], celda=list(libre_cercana(blk, v["pos"])), destinos=v["destinos"]) for v in VIAS])
    obst = dict(rects=[[n, [round(x, 2) for x in b]] for n, b in OBS],
                poligonos=[r for g in BARRERAS_INT for r in ([anillos(g)] if not g.is_empty else [])])
    json.dump(grid, open(f"{OUT}/grid_export.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(obst, open(f"{OUT}/obstaculos_export.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("exportado: celdas", NX * NY, "| libres", int((~blk).sum()), "| anclas", len(anc), "| polígonos", len(obst["poligonos"]), "| rects", len(OBS))
    sys.exit(0)

# --- modo RUTA_PARES: ruta desde cualquier pasillo (donde está el cliente) a cualquier otro pasillo ---
# El origen y el destino usan la misma cara que ya se eligió para llegar desde la entrada (salidas/rutas_destinos.json),
# así que el producto queda en el mismo lado sin importar desde dónde se calcule. Una búsqueda por origen (Dijkstra) y se reconstruye cada destino.
if os.environ.get("RUTA_PARES"):
    rd = json.load(open(f"{OUT}/rutas_destinos.json", encoding="utf-8"))
    celda_de = {v: anc[tuple(r["cara"].split(":"))] for v, r in rd.items()}
    B = blk.tolist(); pares = {}; cruzan = []
    def dijkstra(src):
        dist = {src: 0.0}; padre = {}; pq = [(0.0, src)]
        while pq:
            d, c = heapq.heappop(pq)
            if d > dist[c]: continue
            for dy, dx, w in N8:
                y, x = c[0] + dy, c[1] + dx
                if not (0 <= y < NY and 0 <= x < NX) or B[y][x]: continue
                if dy and dx and (B[c[0] + dy][c[1]] or B[c[0]][c[1] + dx]): continue
                nd = d + w
                if nd < dist.get((y, x), 1e18): dist[(y, x)] = nd; padre[(y, x)] = c; heapq.heappush(pq, (nd, (y, x)))
        return padre
    for a in sorted(rd):
        padre = dijkstra(celda_de[a]); pares[a] = {}
        for b in sorted(rd):
            if a == b: continue
            c = celda_de[b]; cam = [c]
            while c != celda_de[a]: c = padre[c]; cam.append(c)
            cam.reverse()
            if len(cam) == 1: cam = cam * 2          # dos pasillos que comparten la misma ancla (p. ej. 12a y 13a): ruta de largo cero
            pts = centrar_pasillo([ctr(x) for x in suavizar(blk, cam)])
            if cruza(pts): cruzan.append((a, b))
            pares[a][b] = [[round(x), round(y)] for x, y in pts]
    json.dump(pares, open(f"{OUT}/rutas_pares.json", "w", encoding="utf-8"), separators=(",", ":"))
    print("pares:", sum(len(v) for v in pares.values()), "| cruzan obstáculo:", cruzan[:10], len(cruzan))
    sys.exit(0)

TODOS = bool(os.environ.get("RUTA_TODOS"))
if TODOS: CASOS = ["@" + v for v in todos]
def _mid_cara(c):
    b = c["bbox"]; cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    return {"oeste": (b[0], cy), "este": (b[2], cy), "norte": (cx, b[1]), "sur": (cx, b[3])}[c["cara"]]
for obj in CASOS:
    pedida = None; alterna = False
    if obj.startswith("@"):  # ID visible: se va a la cara más cercana a la entrada (tramos -N/-S incluidos); sin ancla -> cara contraria
        v = obj[1:]
        pref = min((c for c in CARAS if v in c["visibles"]), key=lambda c: math.hypot(_mid_cara(c)[0] - ORIGEN[0], _mid_cara(c)[1] - ORIGEN[1]))
        pedida = pref["cara"]; k0 = (pref["mueble"], pref["cara"]); k1 = (pref["mueble"], OPUESTA[pref["cara"]])
        if k0 in anc: ks = [k0]
        else:
            alterna = True
            ks = [k1] if k1 in anc else [k for k in anc if v in next((c["visibles"] for c in CARAS if c["mueble"] == k[0]), [])]
        if not ks:
            print(obj, "SIN ANCLA alcanzable"); resultados[obj] = None; continue
    if obj.startswith("@"): pass
    elif ":" in obj:  # producto en una cara concreta; si esa cara no tiene ancla se lleva a la cara contraria
        base, pedida = obj.split(":")
        if (base, pedida) in anc: ks = [(base, pedida)]
        else: ks = [(base, OPUESTA[pedida])] if (base, OPUESTA[pedida]) in anc else []; alterna = True
    else:
        ks = [k for k in anc if k[0] == obj or obj in next((c["visibles"] for c in CARAS if c["mueble"] == k[0]), [])]
    if not ks:
        print(obj, "SIN ANCLA alcanzable"); resultados[obj] = None; continue
    via = next((v for v in VIAS if obj.lstrip("@").split(":")[0] in v["destinos"]), None)  # punto obligado (correcciones.json: ruta_via)
    vc = libre_cercana(blk, via["pos"]) if via else None
    mejor = None
    for k in ks:  # varias caras: la más corta
        if vc:
            c1 = astar(blk, s, [vc]); c2 = astar(blk, vc, [anc[k]])
            cam = (c1 + c2[1:]) if (c1 and c2) else None
        else:
            cam = astar(blk, s, [anc[k]])
        if cam and (mejor is None or len(cam) < len(mejor[0])):
            mejor = (cam, k)
    if not mejor:
        print(obj, "A* sin camino"); resultados[obj] = None; continue
    cam, k = mejor
    if vc:
        i = cam.index(vc)
        sm = suavizar(blk, cam[:i + 1]) + suavizar(blk, cam[i:])[1:]
    else:
        sm = suavizar(blk, cam)
    pts = centrar_pasillo([tuple(ORIGEN)] + [ctr(c) for c in sm[1:]])
    cruz = cruza(pts)
    L = largo(pts); instr = instrucciones(pts, f"{obj} (cara {k[1]})")
    if not TODOS: dibujar(obj.replace(":", "_"), pts, pts[-1], obj)
    resultados[obj] = dict(cara=f"{k[0]}:{k[1]}", puntos=[[round(x, 1), round(y, 1)] for x, y in pts], largo_pt=round(L, 1),
                           cruza_obstaculo=cruz, instrucciones=instr, tramos=len(pts) - 1,
                           cara_pedida=pedida, cara_usada=k[1], cara_alterna=alterna, mueble=k[0], via=(list(via['pos']) if via else None))
    print(f"{obj}: cara {k[0]}:{k[1]} | {len(pts) - 1} tramos | {L:.0f} pt | cruza obstáculo: {cruz}")
    for t in instr:
        print("   -", t)
if TODOS:
    json.dump({k[1:]: v for k, v in resultados.items()}, open(f"{OUT}/rutas_destinos.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("destinos:", len(resultados), "| sin ruta:", [k for k, v in resultados.items() if v is None],
          "| cruzan obstáculo:", [k for k, v in resultados.items() if v and v["cruza_obstaculo"]],
          "| cara alterna:", [k for k, v in resultados.items() if v and v["cara_alterna"]])
    sys.exit(0)
json.dump(resultados, open(f"{OUT}/rutas_prueba.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


# --- columna de módulos frente a 29a-39a: ¿cruza por un hueco o rodea? ---
XC = 1265
col = sorted([g.bounds for g in MODS if region_de(g) == "modulos_columna_derecha"], key=lambda b: b[1])
cubierto = [(b[1], b[3]) for b in col if b[0] <= XC <= b[2]]
huecos = []  # intervalos libres entre módulos a lo largo de la columna
cur = None
for a, b in sorted(cubierto):
    if cur is not None and a > cur: huecos.append((cur, a))
    cur = b if cur is None else max(cur, b)
top, bot = min(a for a, _ in cubierto), max(b for _, b in cubierto)
info = {}
for k in COLUMNA:
    r = resultados.get(k)
    if not r: info[k] = dict(estado="sin ruta"); continue
    cr = []
    for (x0, y0), (x1, y1) in zip(r["puntos"], r["puntos"][1:]):
        if (x0 < XC <= x1) or (x1 < XC <= x0): cr.append(y0 + (XC - x0) / (x1 - x0) * (y1 - y0))
    if not cr: info[k] = dict(estado="no cruza la columna (destino del mismo lado)"); continue
    y = cr[0]
    if y < top or y > bot: info[k] = dict(estado="RODEA", y_cruce=round(y)); continue
    h = next(((a, b) for a, b in huecos if a <= y <= b), None)
    info[k] = dict(estado="cruza por hueco" if h else "cruza SOBRE un módulo", y_cruce=round(y),
                   hueco_pt=round(h[1] - h[0], 1) if h else None, hueco_y=[round(h[0]), round(h[1])] if h else None)
    r["columna"] = info[k]
json.dump(resultados, open(f"{OUT}/rutas_prueba.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\ncolumna x={XC}: módulos de y={top:.0f} a y={bot:.0f}; {len(huecos)} huecos de {min(b-a for a,b in huecos):.0f} a {max(b-a for a,b in huecos):.0f} pt")
for k, v in info.items(): print(k, v)

# imagen resumen: rutas 29a-39a superpuestas
PAL = [(.85, .1, .1), (.95, .55, 0), (.55, .45, 0), (.1, .6, .1), (0, .6, .6), (0, .45, .85), (.2, .2, .8), (.5, .2, .8), (.8, .1, .6), (.4, .4, .4), (0, 0, 0)]
doc = pymupdf.open(); pg = doc.new_page(width=2126.25, height=1701)
pg.insert_image(pg.rect, pixmap=bg)
for _, b in OBS: pg.draw_rect(pymupdf.Rect(*b), color=(.75, .78, .85), width=1)
for g in BARRERAS: pg.draw_polyline(list(g.exterior.coords), color=(.9, .45, .1), width=1.2, closePath=True)
for i, k in enumerate(COLUMNA):
    r = resultados.get(k)
    if not r: continue
    c = PAL[i]; off = (i - 5) * 2.5  # desplazamiento leve para que no se tapen
    pts = [(x + off, y + off) for x, y in r["puntos"]]
    for a, b in zip(pts, pts[1:]): pg.draw_line(a, b, color=c, width=4)
    pg.draw_circle(pts[-1], 9, color=c, fill=c); pg.insert_text((pts[-1][0] + 12, pts[-1][1] - 6 + (i % 3) * 14), k, fontsize=22, color=c)
    v = info.get(k, {})
    if v.get("y_cruce"): pg.draw_circle((XC + off, v["y_cruce"] + off), 8, color=c, width=3)
pg.get_pixmap(matrix=pymupdf.Matrix(.8, .8)).save(f"{OUT}/ruta_resumen_columna.png")


# --- fila de módulos sobre la zona c: ¿cruza por un hueco o rodea? ---
FILA = [g.bounds for g in MODS if region_de(g) == "modulos_fila_zona_c"]
if FILA:
    fy0, fy1 = min(b[1] for b in FILA), max(b[3] for b in FILA); fx0, fx1 = min(b[0] for b in FILA), max(b[2] for b in FILA); YM = (fy0 + fy1) / 2
    cub = sorted((b[0], b[2]) for b in FILA if b[1] <= YM <= b[3]); hf = []; cur = None
    for a, b in cub:
        if cur is not None and a > cur: hf.append((cur, a))
        cur = b if cur is None else max(cur, b)
    infoc = {}
    for k in FILA_C:
        r = resultados.get(k)
        if not r: infoc[k] = dict(estado="sin ruta"); continue
        cr = []
        for (x0, y0), (x1, y1) in zip(r["puntos"], r["puntos"][1:]):
            if (y0 < YM <= y1) or (y1 < YM <= y0): cr.append(x0 + (YM - y0) / (y1 - y0) * (x1 - x0))
        if not cr: infoc[k] = dict(estado="no cruza la fila"); continue
        x = cr[0]
        if x < fx0 or x > fx1: infoc[k] = dict(estado="RODEA", x_cruce=round(x)); continue
        h = next(((a, b) for a, b in hf if a <= x <= b), None)
        infoc[k] = dict(estado="cruza por hueco" if h else "cruza SOBRE un módulo", x_cruce=round(x),
                        hueco_pt=round(h[1] - h[0], 1) if h else None, hueco_x=[round(h[0]), round(h[1])] if h else None)
        r["fila_c"] = infoc[k]
    json.dump(resultados, open(f"{OUT}/rutas_prueba.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nfila zona c y={YM:.0f} x {fx0:.0f}-{fx1:.0f}: {len(FILA)} módulos, {len(hf)} huecos de {min(b-a for a,b in hf):.0f} a {max(b-a for a,b in hf):.0f} pt")
    for k, v in infoc.items(): print(k, v)
