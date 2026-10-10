"""Fase 6: mapa del cliente en SVG (paleta Homecenter) + instrucciones de texto, desde el mismo tienda_42.json.
Salida: salidas/mapa_base.svg, salidas/mapa_ruta_<caso>.svg, salidas/instrucciones.json (+ .txt).
Solo marca la ruta hasta la góndola: no hay metros, distancias ni tiempos."""
import json, math, os, sys
from xml.sax.saxutils import escape
from shapely.geometry import box
from shapely.ops import unary_union

RAIZ = os.path.dirname(os.path.abspath(__file__)); os.chdir(RAIZ)
T = json.load(open("salidas/tienda_42.json", encoding="utf-8"))
R = json.load(open("salidas/rutas_prueba.json", encoding="utf-8")) if os.path.exists("salidas/rutas_prueba.json") else {}
F = T["tienda"]["marco"]; ORIGEN = T["accesos"][0]["pos"]
NAVY, AZUL, AMARILLO, ROJO = "#041E7E", "#0072CE", "#F3C702", "#C60202"
GONDOLA, ZONA, PISO, TEXTO = "#D9E4F1", "#EEF2F8", "#FFFFFF", "#12233B"
MODULO, NEUTRO = "#E6ECF5", "#E3EBF5"
FONT = "'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
PAD, HEADER = 40, 120
ENT_X, ENT_Y = 128, 556  # esquina izquierda de la etiqueta de entrada (a la derecha de P. EXH, sobre los postes)
MAP_H = F["y1"] - F["y0"]
FX1 = 1790                       # el plano se muestra solo hasta aquí (lo último con góndolas llega a x=1744): sin la parte de atrás
SW, SH = MAP_H, FX1 - F["x0"]            # ancho y alto del mapa YA girado (pantalla)
W = SW + 2 * PAD
ROT = True                        # mapa girado: la entrada abajo y el recorrido de abajo hacia arriba
# x' = y - y0 ; y' = x1 - x   (giro de 90° en sentido antihorario: la izquierda del plano pasa a ser la parte inferior)
ROTM = f"matrix(0 -1 1 0 {-F['y0']:.1f} {FX1:.1f})"

# ---------- geometría base ----------
def fusionado(m):
    """bbox del mueble fundido con sus cabeceras (la ruta tampoco pasa por encima de las puntas)."""
    b = list(m["bbox"])
    for c in m["atributos"].get("cabeceras", []):
        b = [min(b[0], c["bbox"][0]), min(b[1], c["bbox"][1]), max(b[2], c["bbox"][2]), max(b[3], c["bbox"][3])]
    return b

MUEBLES = [m for m in T["muebles"] if m["tipo"] in ("mueble", "hito", "continuacion", "sin_clasificar")]

# ---------- instrucciones ----------
def dist_pt_rect(p, b):
    dx = max(b[0] - p[0], 0, p[0] - b[2]); dy = max(b[1] - p[1], 0, p[1] - b[3])
    return math.hypot(dx, dy)

def muestras(a, b, paso=20):
    n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / paso))
    return [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n + 1)]

# hitos con nombre de cliente; "Pisos" aparece en varios puntos pero es un solo hito
HITOS_REF = []
for h in T["hitos"]:
    if h["id"] in ("acceso-principal", "maquina-cables"):
        continue
    nom = {"zona-cajas": "los puntos de pago", "rampas": "las rampas eléctricas", "p-exh": "P. EXH", "plataforma": "la plataforma",
           "asadores": "los asadores", "maquina-pinturas": "la máquina de pinturas", "pisos": "la zona de pisos"}.get(h["id"], h["nombre"])
    HITOS_REF.append(dict(id=h["id"], nombre=nom, pos=h["pos"]))
# los hitos con forma (zona-cajas, rampas...) se miden contra su rectángulo; el resto, contra su punto
HITO_RECT = {m["id"]: fusionado(m) for m in T["muebles"] if m["tipo"] == "hito"}

def candidatos(a, b, excluir):
    pts = muestras(a, b)
    out = []
    for h in HITOS_REF:
        if h["id"] in excluir: continue
        d = min(dist_pt_rect(p, HITO_RECT[h["id"]]) if h["id"] in HITO_RECT else math.hypot(p[0] - h["pos"][0], p[1] - h["pos"][1]) for p in pts)
        if d <= 70: out.append((d - 25, h["id"], h["nombre"]))  # los hitos pesan más que una góndola
    for m in T["muebles"]:
        if m["tipo"] != "mueble" or not m["etiquetas"]: continue
        v = m["etiquetas"][0]
        if v in excluir: continue
        d = min(dist_pt_rect(p, fusionado(m)) for p in pts)
        if d <= 60: out.append((d, v, f"la góndola {v}"))
    return sorted(set(out))

def simplificar(pts, max_tramos, fijos=()):
    pts = list(pts)
    def area(i):
        (x0, y0), (x1, y1), (x2, y2) = pts[i - 1], pts[i], pts[i + 1]
        return abs((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)) / 2
    while len(pts) - 1 > max_tramos and len(pts) > 2:
        libres = [i for i in range(1, len(pts) - 1) if pts[i] not in fijos]  # los extremos del cruce de la columna no se quitan
        if not libres: break
        i = min(libres, key=area); pts.pop(i)
    return pts

def giro(a, b, c):
    d1 = (b[0] - a[0], b[1] - a[1]); d2 = (c[0] - b[0], c[1] - b[1])
    return math.degrees(math.atan2(d1[0] * d2[1] - d1[1] * d2[0], d1[0] * d2[0] + d1[1] * d2[1]))

CORR = json.load(open("correcciones.json", encoding="utf-8"))
def _region(id_):
    reg = next(c["region"] for c in CORR if c.get("id") == id_)
    ms = [mo for bl in T["bloques_modulos"] for mo in bl["modulos"] if reg[0] <= (mo[0] + mo[2]) / 2 <= reg[2] and reg[1] <= (mo[1] + mo[3]) / 2 <= reg[3]]
    return min(m[0] for m in ms), min(m[1] for m in ms), max(m[2] for m in ms), max(m[3] for m in ms)
# barreras de módulos con huecos transitables (cierre 0): se describen como "cruza entre los módulos de exhibición"
BARRERAS_TXT = []
for _id, _eje in (("modulos_columna_derecha", 0),):
    x0, y0, x1, y1 = _region(_id)
    BARRERAS_TXT.append(dict(i=_eje, j=1 - _eje, lo=(x0, y0)[_eje], hi=(x1, y1)[_eje], span=((y0, y1), (x0, x1))[_eje]))
TOL = 8
PC_X0, PC_Y0, PC_X1, PC_Y1 = _region("modulos_fila_zona_c")   # fila de módulos = pasillo central de la zona c
PC_BANDA = (PC_Y0 - 45, PC_Y1 + 8)

def es_pasillo_central(a, b):
    """tramo largo y casi horizontal dentro del pasillo central (o que entra a él en diagonal)"""
    return (PC_X0 - 80 <= min(a[0], b[0]) and max(a[0], b[0]) <= PC_X1 + 40 and abs(b[0] - a[0]) >= 100
            and PC_BANDA[0] <= a[1] <= PC_BANDA[1] + 40 and PC_BANDA[0] <= b[1] <= PC_BANDA[1] + 40 and abs(b[1] - a[1]) <= 0.6 * abs(b[0] - a[0]))

def cruza_barrera(a, b):
    """el tramo atraviesa de lado a lado una barrera de módulos (por un hueco); devuelve la barrera o None"""
    for br in BARRERAS_TXT:
        i, j = br["i"], br["j"]
        if not (br["span"][0] <= (a[j] + b[j]) / 2 <= br["span"][1]): continue
        if (a[i] <= br["lo"] + TOL and b[i] >= br["hi"] - TOL) or (b[i] <= br["lo"] + TOL and a[i] >= br["hi"] - TOL): return br
    return None

def largo_pt(a, b): return math.hypot(b[0] - a[0], b[1] - a[1])

_USADOS = set()  # puntos de referencia ya nombrados en la ruta: no se repiten ni siquiera en pasos no consecutivos

def _ref(a, b, destino, previo):
    cand = [c for c in candidatos(a, b, {destino, previo} | _USADOS) if c[1] != previo] or [c for c in candidatos(a, b, {destino, previo}) if c[1] != previo]
    if cand:
        _USADOS.add(cand[0][1]); return "junto a", cand[0][2], cand[0][1]
    if any(c[1] == destino for c in candidatos(a, b, {previo})): return "hasta", f"la góndola {destino}", destino
    return None, None, previo

def referencia_tramo(a, b, destino, previo):
    """(preposición, texto, id): hito/góndola a menos de 60-70 pt; el destino solo si no hay otra cosa; nunca repite el previo.
    En tramos largos (>500 pt) se nombra un segundo punto: uno de la primera mitad y otro de la segunda."""
    if largo_pt(a, b) > 500:
        m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        p1, t1, id1 = _ref(a, m, destino, previo)
        p2, t2, id2 = _ref(m, b, destino, id1)
        if t1 and t2 and p1 == p2 == "junto a" and id1 != id2: return "junto a", f"{t1} y después junto a {t2}", id2
        if t2 and not t1: return p2, t2, id2
        if t1: return p1, t1, id1
    return _ref(a, b, destino, previo)

def _ref_txt(a, b, destino, previo):
    prep, donde, previo = referencia_tramo(a, b, destino, previo)
    return (f"{prep} {donde}" if donde else "por el pasillo"), previo

def _pasos(pts, iv, destino):
    """-> (pasos, fines): fines[k] = punto de la ruta donde termina el paso k"""
    _USADOS.clear()
    pasos, fines = [], []; previo = None; i = 0
    def poner(txt, fin): pasos.append(txt); fines.append(fin)
    if iv is not None and iv >= 1:
        # todo el recorrido compartido hasta el pasillo central de la zona c se cuenta como un solo paso
        p1, t1, id1 = referencia_tramo(pts[0], pts[1], destino, None)
        p2, t2, id2 = referencia_tramo(pts[iv - 1], pts[iv], destino, id1) if iv >= 2 else (None, None, id1)
        partes = []
        if t1: partes.append(f"avanza {p1} {t1}")
        if t2 and id2 != id1 and p2 == "junto a": partes.append(f"baja por el pasillo de {t2}")
        poner("Desde la entrada, " + " y ".join(partes) + " hasta el pasillo central de la zona c."
              if partes else "Desde la entrada, ve hasta el pasillo central de la zona c.", pts[iv])
        previo = id2 or id1; i = iv
    while i < len(pts) - 1:
        a, b = pts[i], pts[i + 1]
        br = cruza_barrera(a, b)
        if es_pasillo_central(a, b):  # pasillo central + bajada por el pasillo de la góndola = un solo paso
            j = i + 1
            while j + 1 < len(pts) and es_pasillo_central(pts[j], pts[j + 1]): j += 1
            if j + 1 < len(pts) and pts[j + 1][1] - pts[j][1] > 40:
                poner(f"Sigue por el pasillo central de la zona c y baja por el pasillo de la góndola {destino}.", pts[j + 1])
                i = j + 1; continue
            poner("Sigue por el pasillo central de la zona c.", pts[j]); i = j; continue
        if br:  # el cruce entre los módulos y el tramo siguiente se cuentan como un solo paso
            k = br["i"]; sentido = 1 if a[k] < b[k] else -1
            borde = br["lo"] if sentido > 0 else br["hi"]
            if abs(a[k] - borde) > 120:  # tramo largo que solo cruza al final: primero se describe el recorrido hasta la barrera
                t = (borde - 12 * sentido - a[k]) / (b[k] - a[k])
                a2 = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
                ref, previo = _ref_txt(a, a2, destino, previo)
                if not pasos: poner(f"Desde la entrada, avanza {ref}.", a2)
                else: poner(f"Gira a la {'derecha' if giro(pts[i - 1], a, b) > 0 else 'izquierda'} y sigue {ref}.", a2)
                a = a2
            if i + 2 < len(pts):
                c = pts[i + 2]; dx, dy = c[0] - b[0], c[1] - b[1]
                verbo = ("baja" if dy > 0 else "sube") if abs(dy) >= abs(dx) else "sigue"
                ref, previo = _ref_txt(b, c, destino, previo)
                poner(f"Cruza entre los módulos de exhibición y {verbo} {ref}.", c)
                i += 2; continue
            resto = abs(b[k] - (br["hi"] if sentido > 0 else br["lo"]))
            if resto > 60:  # el mismo tramo sigue más allá de la barrera hasta la góndola
                verbo = ("baja" if sentido > 0 else "sube") if k == 1 else "sigue"
                poner(f"Cruza entre los módulos de exhibición y {verbo} hasta la góndola {destino}.", b)
            else:
                poner("Cruza entre los módulos de exhibición.", b)
            i += 1; continue
        ref, previo = _ref_txt(a, b, destino, previo)
        if not pasos:
            poner(f"Desde la entrada, avanza {ref}.", b)
        else:
            lado = "derecha" if giro(pts[i - 1], a, b) > 0 else "izquierda"
            poner(f"Gira a la {lado} y sigue {ref}.", b)
        i += 1
    return pasos, fines

def instrucciones(r, destino, mueble_dest, max_pasos=5, con_fines=False):
    """máximo 5 pasos por ruta (salida + giros + llegada)"""
    pts0 = [tuple(p) for p in r["puntos"]]
    via = tuple(r["via"]) if r.get("via") else None
    iv0 = None
    if via:
        d, iv0 = min((math.hypot(p[0] - via[0], p[1] - via[1]), i) for i, p in enumerate(pts0))
        if d > 12: iv0 = None
    lim = []
    for i, p in enumerate(pts0):
        if 0 < i < len(pts0) - 1 and i != iv0 and abs(giro(lim[-1], p, pts0[i + 1])) < 30: continue
        lim.append(p)
    fijos = {p for a, b in zip(lim, lim[1:]) if cruza_barrera(a, b) for p in (a, b)}
    if iv0 is not None: fijos.add(pts0[iv0])
    fijos |= {q for a, b in zip(lim, lim[1:]) if es_pasillo_central(a, b) for q in (a, b)}  # esquinas del pasillo central
    for maxl in (4, 3, 2, 1):
        pts = simplificar(lim, maxl, fijos)
        iv = pts.index(pts0[iv0]) if iv0 is not None and pts0[iv0] in pts else None
        pasos, fines = _pasos(pts, iv, destino)
        if len(pasos) + 1 <= max_pasos: break
    # llegada: lado en que queda la góndola respecto a la dirección final
    a, b = pts[-2], pts[-1]
    cx, cy = (mueble_dest[0] + mueble_dest[2]) / 2, (mueble_dest[1] + mueble_dest[3]) / 2
    h = (b[0] - a[0], b[1] - a[1]); v = (cx - b[0], cy - b[1])
    cruz = h[0] * v[1] - h[1] * v[0]; punto = h[0] * v[0] + h[1] * v[1]
    n = math.hypot(*h) * math.hypot(*v) or 1
    pos = "frente a ti" if abs(cruz) / n < .35 and punto > 0 else ("a tu derecha" if cruz > 0 else "a tu izquierda")
    pasos.append(f"Llegaste: la góndola {destino} queda {pos}."); fines.append(pts[-1])
    if r.get("cara_alterna"):
        pasos[-1] += " Tu producto está en el lado contrario de esta góndola: rodéala; el mapa lo marca."
    return (pasos, fines) if con_fines else pasos

# ---------- SVG ----------
VENTANA = None  # (x0, y0, x1, y1) del recorte: las etiquetas que no caben enteras se omiten

def pill(x, y, txt, fill=AZUL, color="#fff", size=21, vertical=False, stroke=None, gid=None, barra=False):
    w = len(txt) * size * .6 + size * .9; h = size * 1.55
    # el mapa se gira -90°: para que el texto quede horizontal en pantalla la etiqueta se gira +90° sobre su centro;
    # solo las barras delgadas (que en pantalla quedan verticales) conservan el texto en vertical
    giro = (0 if barra else 90) if ROT else (-90 if vertical else 0)
    pw, ph = (w, h) if giro == 0 else (h, w)
    if VENTANA:
        if x - pw / 2 < VENTANA[0] + 4 or x + pw / 2 > VENTANA[2] - 4 or y - ph / 2 < VENTANA[1] + 4 or y + ph / 2 > VENTANA[3] - 4: return ""
    rot = f' transform="rotate({giro} {x:.1f} {y:.1f})"' if giro else ""
    rot = (f' id="{gid}"' if gid else "") + f' class="pl" data-b="{x - pw / 2:.0f} {y - ph / 2:.0f} {x + pw / 2:.0f} {y + ph / 2:.0f}"' + rot
    st = f' stroke="{stroke}" stroke-width="3"' if stroke else ""
    return (f'<g{rot}><rect x="{x - w / 2:.1f}" y="{y - h / 2:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{h / 2:.1f}" fill="{fill}"{st}/>'
            f'<text x="{x:.1f}" y="{y + size * .36:.1f}" text-anchor="middle" font-size="{size}" font-weight="700" fill="{color}">{escape(txt)}</text></g>')

def rect(b, fill, rx=7, extra="", ident=None):
    return f'<rect{" id=" + chr(34) + ident + chr(34) if ident else ""} x="{b[0]:.1f}" y="{b[1]:.1f}" width="{b[2] - b[0]:.1f}" height="{b[3] - b[1]:.1f}" rx="{rx}" fill="{fill}"{extra}/>'

def _path(g):
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in g.exterior.coords) + "Z"

def zonas_svg():
    out = []
    for z in "abc":
        ms = [m for m in T["muebles"] if m["tipo"] == "mueble" and m["etiquetas"] and m["etiquetas"][0][2] == z]
        # zona derecha (filas 25a-45a con sus continuaciones): un solo bloque redondeado, sin muescas entre góndolas
        der = [m for m in ms + [x for x in T["muebles"] if x["tipo"] == "continuacion"] if (m["bbox"][0] + m["bbox"][2]) / 2 > 1300]
        resto = [m for m in ms if m not in der]
        polys = []
        if resto:
            u = unary_union([box(*fusionado(m)).buffer(26, join_style=2) for m in resto]).buffer(-26 + 8).buffer(0)
            polys += list(u.geoms) if hasattr(u, "geoms") else [u]
        if der:
            polys.append(box(*unary_union([box(*fusionado(m)) for m in der]).bounds).buffer(24))  # rectángulo redondeado: sin muescas ni biseles
        marco = box(F['x0'] + 8, F['y0'] + 8, FX1 - 8, F['y1'] - 8)
        for g in polys:
            g = g.intersection(marco)  # el tinte nunca sale del marco de la tienda
            if g.is_empty or g.geom_type != 'Polygon': continue
            out.append(f'<path d="{_path(g)}" fill="{ZONA}" stroke="{ZONA}" stroke-width="30" stroke-linejoin="round"/>')
    return "\n".join(out)

# ---------- segmentación por familia de producto (color pastel con opacidad baja) ----------
def _cargar_familias():
    cfg = json.load(open("categorias_familia.json", encoding="utf-8"))
    pas = json.load(open("salidas/categoria_por_pasillo.json", encoding="utf-8")) if os.path.exists("salidas/categoria_por_pasillo.json") else {}
    cats = [(c["nombre"], c["color"]) for c in cfg["categorias"]] + [(cfg["por_revisar"]["nombre"], cfg["por_revisar"]["color"])]
    return cfg.get("opacidad", 0.2), cats, pas

def _grupos_pasillo():
    """ID visible del pasillo -> [(caja, id del mueble)] (tramos N/S y continuaciones incluidos)"""
    g = {}
    for m in T["muebles"]:
        if m["tipo"] in ("mueble", "hito") and m["etiquetas"]:
            for e in m["etiquetas"]: g.setdefault(e, []).append((fusionado(m), m["id"]))
        elif m["tipo"] == "continuacion" and m.get("continuacion_de"):
            pid = next((x["etiquetas"][0] for x in T["muebles"] if x["id"] == m["continuacion_de"] and x["etiquetas"]), None)
            if pid: g.setdefault(pid, []).append((m["bbox"], m["id"]))
    return g

def familias_halo(destino_id=None):
    """fondo de color detrás de cada pasillo (y un velo leve sobre sus góndolas, bajo las etiquetas); el destino queda amarillo"""
    op, _, pas = _cargar_familias()
    halos, velos = [], []
    for pid, cajas in _grupos_pasillo().items():
        info = pas.get(pid)
        if not info: continue
        u = unary_union([box(*b).buffer(9) for b, _ in cajas])
        for poly in (u.geoms if hasattr(u, "geoms") else [u]):
            halos.append(f'<path d="{_path(poly)}" fill="{info["color"]}" fill-opacity="{op}"/>')
        for b, mid in cajas: velos.append((mid, b, info["color"]))
    return "\n".join(halos), velos, op

def familias_velo(velos, op, destino_id):
    out, vistos = [], set()
    for mid, b, color in velos:
        if (destino_id is not None and mid == destino_id) or mid in vistos: continue
        vistos.add(mid)
        out.append(rect(b, color, 7, f' fill-opacity="{op}"', ident=f"v-{mid}"))
    return "".join(out)

def mapa_base(destino_id=None, ruta=None, transform=True, familias=True):
    g = [f'<g id="mapa" transform="translate({PAD},{HEADER + PAD}) {ROTM}">' if transform else f'<g id="mapa" transform="{ROTM}">']
    g.append(f'<rect x="{F["x0"]}" y="{F["y0"]}" width="{FX1 - F["x0"]}" height="{MAP_H}" rx="26" fill="{PISO}" stroke="#C9D6E8" stroke-width="4"/>')
    g.append(f'<g id="zonas">{zonas_svg()}</g>')
    if familias:
        _halo, _velos, _op = familias_halo(destino_id)
        g.append(f'<g id="familias">{_halo}</g>')
    g.append('<g id="modulos">' + "".join(rect(mo, MODULO, 4) for b in T["bloques_modulos"] for mo in b["modulos"])
             + "".join(rect(o["bbox"], MODULO, 6) for o in T.get("obstaculos_extra", [])) + "</g>")
    g.append('<g id="gondolas">')
    for m in MUEBLES:
        b = fusionado(m); dest = destino_id is not None and m["id"] == destino_id
        if b[0] >= FX1: continue                       # bloque de la parte de atrás (fuera de lo que se muestra)
        if m["tipo"] == "sin_clasificar": g.append(rect(b, NEUTRO, 7)); continue
        if m["id"] == "zona-cajas": g.append(rect(b, "#F6DCDC", 9, f' stroke="{ROJO}" stroke-width="3"')); continue
        g.append(rect(b, AMARILLO if dest else GONDOLA, 7, f' stroke="{NAVY}" stroke-width="4"' if dest else "", ident=f"g-{m['id']}"))
    g.append("</g>")
    if familias: g.append(f'<g id="familias-velo">{familias_velo(_velos, _op, destino_id)}</g>')
    g.append('<g id="etiquetas">')
    for m in MUEBLES:
        b = fusionado(m); w, h = b[2] - b[0], b[3] - b[1]; cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        if VENTANA:  # la etiqueta se centra en la parte visible de la góndola
            vb = [max(b[0], VENTANA[0] + 6), max(b[1], VENTANA[1] + 6), min(b[2], VENTANA[2] - 6), min(b[3], VENTANA[3] - 6)]
            if vb[2] <= vb[0] or vb[3] <= vb[1]: continue
            cx, cy = (vb[0] + vb[2]) / 2, (vb[1] + vb[3]) / 2
        dest = destino_id is not None and m["id"] == destino_id
        col, fil = (NAVY, AMARILLO) if dest else ("#fff", AZUL)
        if m["id"] == "zona-cajas": g.append(pill(cx, cy, "Puntos de pago", ROJO, "#fff", 26, True)); continue
        if m["id"] == "rampas": g.append(pill(cx, cy, "Rampas eléctricas", NAVY, "#fff", 24, True)); continue
        if m["id"] == "p-exh": g.append(pill(cx, b[1] + 60, "P. EXH", NAVY, "#fff", 21, True)); continue
        if m["id"] == "maquina-pinturas": g.append(pill(cx, cy, "Pinturas", NAVY, "#fff", 21)); continue
        if m["id"] == "plataforma": g.append(pill(cx, cy, "Plataforma", NAVY, "#fff", 24)); g.append(pill(cx - 46, cy, "12a · 13a", AZUL, "#fff", 20)); continue
        if m["tipo"] == "mueble" and m["etiquetas"]:
            vert = h >= 2 * w and w < 70
            px = (max(b[0] + 60, VENTANA[0] + 40) if VENTANA else b[0] + 60) if dest and w >= 3 * h else cx  # en barras anchas el marcador de destino cae al centro: la etiqueta se corre
            g.append(pill(px, cy, m["etiquetas"][0], fil, col, 21, vert, NAVY if dest else None, gid=f"l-{m['id']}", barra=(not vert) and h < 70))
            if m["etiquetas"][0] == "16b": g.append(pill(cx - 50, cy, "Pisos", NAVY, "#fff", 21))
    g.append(pill(PC_X0 + 105, (PC_Y0 + PC_Y1) / 2, "Pasillo central", AZUL, "#fff", 17))
    for h in T["hitos"]:
        if h["id"] == "asadores": g.append(pill(h["pos"][0], h["pos"][1] - 2, "Asadores", NAVY, "#fff", 19))
        if h["id"] == "pisos" and h["pos"][1] < 700 and h["pos"][0] < 1100: g.append(pill(h["pos"][0], h["pos"][1] + 24, "Pisos", NAVY, "#fff", 19))
    g.append("</g>")
    if ruta:
        pts = [tuple(p) for p in ruta["puntos"]]; d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        g.append(f'<g id="ruta"><path d="{d}" fill="none" stroke="#fff" stroke-width="17" stroke-linecap="round" stroke-linejoin="round" opacity=".92"/>'
                 f'<path class="ruta" d="{d}" fill="none" stroke="{NAVY}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="22 16"/></g>')
        ex, ey = pts[-1]
        g.append(f'<g id="destino"><circle cx="{ex:.1f}" cy="{ey:.1f}" r="15" fill="{AMARILLO}" stroke="{NAVY}" stroke-width="5"/>'
                 f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="5" fill="{NAVY}"/></g>')
        if ruta.get("cara_alterna"): g.append(pill(ex, ey - 44, "Lado contrario", "#fff", NAVY, 20, stroke=AMARILLO))
        g.append(f'<circle cx="{ORIGEN[0]}" cy="{ORIGEN[1]}" r="17" fill="{NAVY}" stroke="#fff" stroke-width="6"/>')
        g.append(f'<line x1="{ORIGEN[0]}" y1="{ORIGEN[1] - 14}" x2="{ORIGEN[0]}" y2="{ENT_Y + 16}" stroke="{NAVY}" stroke-width="4"/>')
        g.append(pill(ENT_X + 66, ENT_Y, "Estás aquí", NAVY, "#fff", 20))
    else:
        g.append('<g id="ent-base">')
        g.append(f'<line x1="{ORIGEN[0]}" y1="{ORIGEN[1] - 14}" x2="{ORIGEN[0]}" y2="{ENT_Y + 16}" stroke="{ROJO}" stroke-width="4"/>')
        g.append(pill(ENT_X + 76, ENT_Y, "Entrada/Salida", ROJO, "#fff", 18))
        g.append(f'<circle cx="{ORIGEN[0]}" cy="{ORIGEN[1]}" r="13" fill="{ROJO}" stroke="#fff" stroke-width="5"/>')
        g.append('</g>')
    g.append("</g>")
    return "\n".join(g)

def svg(titulo, subtitulo, cuerpo, pie_h, pie, map_h=None):
    mh = SH if map_h is None else map_h
    H = HEADER + mh + 2 * PAD + pie_h
    css = ("text{font-family:" + FONT + "}@keyframes marcha{to{stroke-dashoffset:-76}}"
           ".ruta{animation:marcha 1.6s linear infinite}@media (prefers-reduced-motion:reduce){.ruta{animation:none}}")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}" role="img" aria-label="{escape(titulo)}">'
            f'<style>{css}</style><rect width="{W:.0f}" height="{H:.0f}" fill="#fff"/>'
            f'<rect width="{W:.0f}" height="{HEADER}" fill="{NAVY}"/>'
            f'<text x="{PAD}" y="62" font-size="46" font-weight="700" fill="#fff">{escape(titulo)}</text>'
            f'<text x="{PAD}" y="102" font-size="28" fill="#CFE0F5">{escape(subtitulo)}</text>'
            f'{cuerpo}<g id="pie" transform="translate(0,{HEADER + mh + 2 * PAD})">{pie}</g></svg>')

def recorte(ruta, pad=170, min_w=1000, min_h=720):
    """ventana del mapa alrededor de la ruta (entrada, tramos y destino); se amplía a un mínimo y se recorta al marco de la tienda"""
    xs = [p[0] for p in ruta["puntos"]]; ys = [p[1] for p in ruta["puntos"]]
    x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; cw, ch = max(x1 - x0, min_w), max(y1 - y0, min_h)
    cw, ch = min(cw, FX1 - F["x0"]), min(ch, MAP_H)
    x0 = min(max(cx - cw / 2, F["x0"]), FX1 - cw); y0 = min(max(cy - ch / 2, F["y0"]), F["y1"] - ch)
    return x0, y0, cw, ch

def cuerpo_recorte(inner, crop):
    x0, y0, cw, ch = crop
    vx, vy, vw, vh = y0 - F["y0"], FX1 - (x0 + cw), ch, cw        # la misma ventana, ya girada
    s = (W - 2 * PAD) / vw; mh = vh * s
    return (f'<svg x="{PAD}" y="{HEADER + PAD}" width="{W - 2 * PAD:.0f}" height="{mh:.1f}" viewBox="{vx:.1f} {vy:.1f} {vw:.1f} {vh:.1f}" overflow="hidden">'
            f'{inner}</svg><rect x="{PAD}" y="{HEADER + PAD}" width="{W - 2 * PAD:.0f}" height="{mh:.1f}" rx="26" fill="none" stroke="#C9D6E8" stroke-width="4"/>'), mh

def pie_leyenda(base=True):
    """pie con la leyenda: colores del mapa (solo en el mapa base) y categorías"""
    _, cats, _ = _cargar_familias()
    items = ([(GONDOLA, "Góndola", None), (AMARILLO, "Tu destino", NAVY), (ROJO, "Cajas y entrada / salida", None), (ZONA, "Zonas a, b y c", None), ("ruta", "Tu ruta", None)] if base else []) \
            + [(c, n, "cat") for n, c in cats]
    out, x, fila = [], PAD, 0
    for fill, txt, st in items:
        ancho = 52 + len(txt) * 16 + 40 if fill != "ruta" else 106 + len(txt) * 16 + 20
        if st == "cat": ancho = 44 + len(txt) * 13 + 30
        if x + ancho > W - PAD: x, fila = PAD, fila + 1
        y = 34 + fila * 56
        if fill == "ruta":
            out.append(f'<line x1="{x}" y1="{y + 19}" x2="{x + 90}" y2="{y + 19}" stroke="{NAVY}" stroke-width="9" stroke-dasharray="22 16" stroke-linecap="round"/>')
            out.append(f'<text x="{x + 106}" y="{y + 28}" font-size="28" fill="{TEXTO}">{txt}</text>')
        elif st == "cat":
            out.append(f'<rect x="{x}" y="{y + 4}" width="30" height="28" rx="7" fill="{fill}" fill-opacity=".55" stroke="{fill}" stroke-width="2"/>')
            out.append(f'<text x="{x + 42}" y="{y + 27}" font-size="22" fill="{TEXTO}">{escape(txt)}</text>')
        else:
            out.append(f'<rect x="{x}" y="{y}" width="38" height="38" rx="9" fill="{fill}"' + (f' stroke="{st}" stroke-width="4"' if st else ' stroke="#C9D6E8" stroke-width="2"') + "/>")
            out.append(f'<text x="{x + 52}" y="{y + 28}" font-size="28" fill="{TEXTO}">{escape(txt)}</text>')
        x += ancho
    return "".join(out), 34 + (fila + 1) * 56 + 10

# ---------- salidas ----------
def guardar(nombre, s):
    open(f"salidas/{nombre}.svg", "w", encoding="utf-8").write(s)

def svg_ruta(r, visible, recortada=False):
    """SVG completo (cabecera, mapa y pasos) de una ruta; devuelve (svg, pasos)"""
    global VENTANA
    mid = r["cara"].split(":")[0]
    m = next(x for x in T["muebles"] if x["id"] == mid)
    pasos = instrucciones(r, visible, fusionado(m))          # solo para quien llame (línea de comandos); el mapa ya no lleva texto de indicaciones
    sub = f"Ruta a la góndola {visible}" + (" · por el lado contrario" if r.get("cara_alterna") else "")
    if not recortada:
        _pie, _ph = pie_leyenda(base=False)
        return svg("Homecenter Calle 80", sub, mapa_base(destino_id=mid, ruta=r), _ph, _pie), pasos
    cr = recorte(r); VENTANA = (cr[0], cr[1], cr[0] + cr[2], cr[1] + cr[3])
    try: cuerpo, mh = cuerpo_recorte(mapa_base(destino_id=mid, ruta=r, transform=False), cr)
    finally: VENTANA = None
    _pie, _ph = pie_leyenda(base=False)
    return svg("Homecenter Calle 80", sub, cuerpo, _ph, _pie, map_h=mh), pasos

def svg_mapa_pagina():
    """mapa base sin ruta, para incrustar en la página (la ruta se dibuja en el navegador, dentro de una capa con el mismo giro)"""
    x0, y0, w, h = -14, -14, SW + 28, SH + 28
    return (f'<svg id="mapa-svg" xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {w} {h}" role="img" aria-label="Mapa de la tienda">'
            f'{mapa_base(transform=False)}<g id="capa-ruta" transform="{ROTM}"></g></svg>'), (x0, y0, w, h)

def _largo_hasta(pts, p):
    """longitud recorrida sobre la polilínea hasta el punto más cercano a p"""
    mejor, acum, mejor_len = 1e18, 0.0, 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        dx, dy = x1 - x0, y1 - y0; l2 = dx * dx + dy * dy
        t = 0 if l2 == 0 else max(0, min(1, ((p[0] - x0) * dx + (p[1] - y0) * dy) / l2))
        d = math.hypot(x0 + t * dx - p[0], y0 + t * dy - p[1]); l = math.sqrt(l2)
        if d <= mejor + 1e-6: mejor, mejor_len = d, acum + t * l
        acum += l
    return mejor_len

def datos_destino(r, visible):
    """lo que la página necesita de una ruta: puntos, góndola destino, pasos, dónde termina cada paso y ventana de recorte"""
    mid = r["cara"].split(":")[0]
    m = next(x for x in T["muebles"] if x["id"] == mid)
    cr = recorte(r)
    pasos, fines = instrucciones(r, visible, fusionado(m), con_fines=True)
    pts = [tuple(p) for p in r["puntos"]]
    total = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
    fin, prev = [], 0.0
    for f in fines:
        v = max(prev, _largo_hasta(pts, f)); fin.append(round(v, 1)); prev = v
    fin[-1] = round(total, 1)          # el último paso (llegada) termina en el destino
    if len(fin) > 1: fin[-2] = round(total, 1) if fin[-2] > total - 25 else fin[-2]  # el último tramo de camino llega al destino
    return dict(p=[[round(x), round(y)] for x, y in r["puntos"]], m=mid, alt=bool(r.get("cara_alterna")),
                pasos=pasos, fin=fin, L=round(total, 1), rec=[round(v) for v in cr], gb=[round(v) for v in fusionado(m)])

def main():
    _pie, _ph = pie_leyenda()
    guardar("mapa_base_sin_familias", svg("Homecenter Calle 80", "Mapa de la tienda", mapa_base(familias=False), _ph, _pie))
    guardar("mapa_base", svg("Homecenter Calle 80", "Mapa de la tienda", mapa_base(), _ph, _pie))
    EJEMPLOS = [("05b", "05b"), ("14c", "14c"), ("39a", "39a")]
    COLUMNA = [(k, k) for k in ["29a", "30a", "31a", "32a", "33a", "34a", "35a", "36a", "37a", "38a"]]
    FILA_C = [(k, k) for k in ["05c", "07c", "08c", "09c"] + [f"{n}c" for n in range(10, 22)] if k != "14c"]
    EXTRA = [("15b:este", "15b")]  # cara sin ancla -> cara contraria
    textos = {}
    for clave, visible in EJEMPLOS + COLUMNA + FILA_C + EXTRA:
        r = R[clave]
        nombre = "mapa_ruta_" + clave.replace(":", "_")
        completo, pasos = svg_ruta(r, visible, False); guardar(nombre, completo)
        rec, _ = svg_ruta(r, visible, True); guardar(nombre + "_recorte", rec)
        textos[clave] = pasos
    json.dump(textos, open("salidas/instrucciones.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open("salidas/instrucciones.txt", "w", encoding="utf-8") as f:
        for k, v in textos.items():
            f.write(f"Ruta a {k}" + chr(10) + "".join(f"  {i + 1}. {p}" + chr(10) for i, p in enumerate(v)) + chr(10))
    print(open("salidas/instrucciones.txt", encoding="utf-8").read())

if __name__ == "__main__":
    main()
