"""Nombres de zona del mapa (como el diagrama oficial de la tienda): Aseo, Iluminación, Pinturas, Pisos & Paredes...
Cada pasillo toma el nombre de su familia predominante; los pasillos vecinos con el mismo nombre forman una zona y el rótulo
se coloca donde menos estorbe a las etiquetas de las góndolas. Solo dibuja texto: no cambia rutas ni búsqueda."""
import collections, json, os, re
from xml.sax.saxutils import escape

RAIZ = os.path.dirname(os.path.abspath(__file__))

# familia del catálogo -> nombre en el diagrama de la tienda
NOMBRE = {
    "PINTURA Y ACCESORIOS": "Pinturas", "ASEO": "Aseo", "ILUMINACION Y VENTILADORES": "Iluminación", "PISOS": "Pisos & Paredes",
    "MENAJE": "Hogar & Menaje", "AIRE LIBRE": "Aire libre", "JARDIN": "Jardín", "DECORACION": "Decoración",
    "ORGANIZACION": "Organización", "MUEBLES": "Muebles", "ELECTROHOGAR": "Electrohogar", "BANOS Y COCINAS": "Baños & Cocinas",
    "PLOMERIA / GASFITERIA": "Plomería", "FERRETERIA": "Ferretería", "HERRAMIENTAS Y MAQUINARIAS": "Herramientas",
    "ACCESORIOS AUTOMOVILES": "Autos", "CASA INTELIGENTE": "Casa inteligente", "ELECTRICIDAD": "Eléctricos",
    "PUERTAS/VENTANAS/MOLDURAS": "Puertas & Ventanas", "TABIQUERIA/TECHUMBRE/AISLACION": "Cielo rasos",
}
_CACHE = {}
FX1_MAPA = 1790  # el mapa se muestra solo hasta aquí (igual que FX1 de mapa_cliente)
MIN_SKU = 30  # un pasillo con menos SKU de la familia no rotula zona (evita nombres por 5 o 10 productos sueltos)


def zona_por_pasillo():
    """pasillo del plano -> nombre de zona, según la familia con más SKU entre las que tienen nombre en el diagrama"""
    prods = json.load(open(os.path.join(RAIZ, "salidas", "catalogo.json"), encoding="utf-8"))
    por = collections.defaultdict(lambda: collections.defaultdict(set))
    for p in prods:
        for u in p["ubic"]:
            if u["id_plano"] and p["familia"] in NOMBRE: por[u["id_plano"]][p["familia"]].add(p["sku"])
    zona = {}
    for pas, fam in por.items():
        f, skus = max(fam.items(), key=lambda kv: (len(kv[1]), kv[0]))
        if len(skus) >= MIN_SKU: zona[pas] = NOMBRE[f]
    return zona


def _rects_pantalla(b, y0, fx1):
    """caja del plano (x0,y0,x1,y1) -> caja en pantalla (mapa girado -90°)"""
    return (b[1] - y0, fx1 - b[2], b[3] - y0, fx1 - b[0])


def _solape(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0]); h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0.0


def agrupar(grupos_pasillo):
    """zonas = pasillos vecinos (mismo bloque a/b/c, números seguidos) con el mismo nombre de familia"""
    zp = zona_por_pasillo()
    por_bloque = collections.defaultdict(list)
    for pid in zp:
        if pid in grupos_pasillo: por_bloque[pid[-1]].append(pid)
    grupos = []
    for _, ids in sorted(por_bloque.items()):
        ids.sort(key=lambda i: (int(i[:2]), i))
        for pid in ids:
            if grupos and grupos[-1]["nombre"] == zp[pid] and grupos[-1]["bloque"] == pid[-1]: grupos[-1]["ids"].append(pid)
            else: grupos.append(dict(nombre=zp[pid], bloque=pid[-1], ids=[pid]))
    return grupos


def _marco():
    return json.load(open(os.path.join(RAIZ, "salidas", "tienda_42.json"), encoding="utf-8"))["tienda"]["marco"]


def regiones(grupos, grupos_pasillo):
    """Las zonas del bloque «a» ocupan su bloque completo, como en el diagrama oficial (no solo las góndolas con etiqueta):
    - columnas de arriba (pasillos largos en vertical, 22a–45a): de la pared a la línea común del fondo, repartiendo el ancho
      entre zonas vecinas a la mitad del hueco que las separa;
    - fila de la izquierda (pasillos en horizontal, 02a–21a): de la pared izquierda al borde de sus góndolas, repartiendo
      el alto igual entre zonas vecinas. Así entran las góndolas sin etiqueta y los huecos del fondo.
    Devuelve índice del grupo -> caja del plano (x0, y0, x1, y1). Las zonas de los bloques b y c siguen el contorno de sus góndolas."""
    marco = _marco()
    def caja(g):
        bs = [b for pid in g["ids"] for b, _ in grupos_pasillo[pid]]
        return (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))
    def clase(g):
        if g["bloque"] != "a": return None
        return "col" if int(g["ids"][0][:2]) >= 22 else "fila"  # 22a–45a: pasillos largos en vertical; 02a–21a: en horizontal
    out = {}
    cols = sorted((i for i, g in enumerate(grupos) if clase(g) == "col"), key=lambda i: caja(grupos[i])[1])
    if cols:
        fondo = min(caja(grupos[i])[0] for i in cols) - 14      # línea común en la que terminan todas las zonas de arriba
        for k, i in enumerate(cols):
            c = caja(grupos[i])
            lo = marco["y0"] if k == 0 else (caja(grupos[cols[k - 1]])[3] + c[1]) / 2
            hi = marco["y1"] if k == len(cols) - 1 else (c[3] + caja(grupos[cols[k + 1]])[1]) / 2
            out[i] = (fondo, lo, FX1_MAPA, hi)
    filas = sorted((i for i, g in enumerate(grupos) if clase(g) == "fila"), key=lambda i: caja(grupos[i])[0])
    if filas:
        ancho = max(caja(grupos[i])[3] for i in filas) + 14       # borde de las góndolas de la fila (con sus cabeceras)
        for k, i in enumerate(filas):
            c = caja(grupos[i])
            lo = c[0] - 14 if k == 0 else (caja(grupos[filas[k - 1]])[2] + c[0]) / 2
            hi = c[2] + 14 if k == len(filas) - 1 else (c[2] + caja(grupos[filas[k + 1]])[0]) / 2
            out[i] = (lo, marco["y0"], hi, ancho)
    # bloque c (columna derecha, pasillos en horizontal apilados): cada zona toma el tramo entre sus vecinas, a la mitad del hueco,
    # y deja una separación de 3 pt con cada una para que se vean como bloques distintos (Ferretería / Herramientas / Autos...)
    cs = sorted((i for i, g in enumerate(grupos) if g["bloque"] == "c"), key=lambda i: caja(grupos[i])[0])
    SEP = 3
    for k, i in enumerate(cs):
        c = caja(grupos[i])
        lo = c[0] - 14 if k == 0 else (caja(grupos[cs[k - 1]])[2] + c[0]) / 2 + SEP
        hi = c[2] + 14 if k == len(cs) - 1 else (c[2] + caja(grupos[cs[k + 1]])[0]) / 2 - SEP
        out[i] = (lo, c[1] - 8, hi, c[3] + 8)
    return out


def _oscuro(hexcolor, k=0.45, hacia=(4, 30, 126)):
    """mezcla el color de la categoría con el azul oscuro de la marca: borde legible sin gritar"""
    c = [int(hexcolor[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02X%02X%02X" % tuple(round(a * (1 - k) + b * k) for a, b in zip(c, hacia))


def _trazo(poly):
    def anillo(pts): return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z"
    return " ".join([anillo(poly.exterior.coords)] + [anillo(i.coords) for i in poly.interiors])


def svg_bordes(grupos_pasillo):
    """contorno de cada zona (como los bloques del diagrama oficial): une las góndolas del grupo y cierra los huecos entre ellas"""
    from shapely.geometry import box
    from shapely.ops import unary_union
    cat = json.load(open(os.path.join(RAIZ, "salidas", "categoria_por_pasillo.json"), encoding="utf-8"))
    out = ['<g id="zonas-borde" pointer-events="none" fill="none" stroke-linejoin="round">']
    grupos = agrupar(grupos_pasillo)
    reg = regiones(grupos, grupos_pasillo)
    for i, g in enumerate(grupos):
        cajas = [box(*reg[i])] if i in reg else [box(*b) for pid in g["ids"] for b, _ in grupos_pasillo[pid]]
        u = unary_union(cajas).buffer(24, join_style=2).buffer(-10, join_style=2) if i not in reg else cajas[0]
        color = _oscuro(cat.get(g["ids"][0], {}).get("color", "#9E9E9E"))
        for poly in (u.geoms if hasattr(u, "geoms") else [u]):
            out.append(f'<path d="{_trazo(poly)}" stroke="{color}" stroke-opacity=".8" stroke-width="5" fill-rule="evenodd"/>')
    out.append("</g>")
    return "".join(out)


def zonas(grupos_pasillo, cajas_etiquetas, y0, fx1):
    """lista de rótulos: nombre, centro en pantalla, tamaño de letra y si va en vertical.
    grupos_pasillo: pasillo -> [(bbox_plano, id)]; cajas_etiquetas: cajas del plano de las etiquetas ya dibujadas."""
    grupos = agrupar(grupos_pasillo)
    pills = [_rects_pantalla(b, y0, fx1) for b in cajas_etiquetas]
    ocupados, salida = [], []
    # primero las zonas más grandes: eligen sitio antes que las pequeñas
    reg = regiones(grupos, grupos_pasillo)
    for i, g in enumerate(grupos):
        cajas = [_rects_pantalla(reg[i], y0, fx1)] if i in reg else [_rects_pantalla(b, y0, fx1) for pid in g["ids"] for b, _ in grupos_pasillo[pid]]
        B = (min(c[0] for c in cajas), min(c[1] for c in cajas), max(c[2] for c in cajas), max(c[3] for c in cajas))
        g["caja"] = B; g["cajas"] = cajas
    for g in sorted(grupos, key=lambda g: -((g["caja"][2] - g["caja"][0]) * (g["caja"][3] - g["caja"][1]))):
        B, cajas, n = g["caja"], g["cajas"], len(g["nombre"])
        mejor = None
        for size in (30, 26, 22, 18, 16, 14):
            largo, alto = n * size * 0.58, size * 1.1
            for vertical in ((False, True) if (B[2] - B[0]) >= (B[3] - B[1]) else (True, False)):
                tw, th = (alto, largo) if vertical else (largo, alto)
                if tw > B[2] - B[0] + 2 or th > B[3] - B[1] + 2: continue
                cx0, cy0 = (B[0] + B[2]) / 2, (B[1] + B[3]) / 2
                paso = 6
                cx = B[0] + tw / 2
                while cx <= B[2] - tw / 2 + 0.01:
                    cy = B[1] + th / 2
                    while cy <= B[3] - th / 2 + 0.01:
                        r = (cx - tw / 2, cy - th / 2, cx + tw / 2, cy + th / 2)
                        # el texto debe caer sobre góndolas de la zona (no en pasillos en blanco)
                        sobre = sum(_solape(r, c) for c in cajas) / (tw * th)
                        pen = sum(_solape(r, p) for p in pills) * 3 + sum(_solape(r, o) for o in ocupados) * 3
                        pen += (1 - sobre) * tw * th * 0.5 + ((cx - cx0) ** 2 + (cy - cy0) ** 2) ** 0.5 * 0.05
                        if mejor is None or pen < mejor[0] - 1e-9: mejor = (pen, size, vertical, cx, cy, r)
                        cy += paso
                    cx += paso
            if mejor and mejor[0] < 16: break  # cabe sin estorbar: se queda con la letra más grande
        if mejor:
            _, size, vertical, cx, cy, r = mejor
            ocupados.append(r)
            salida.append(dict(nombre=g["nombre"], x=cx, y=cy, size=size, vertical=vertical))
    return salida


def svg_zonas(rotulos, y0, fx1):
    """<g> con los rótulos, en coordenadas del plano (el grupo del mapa ya viene girado): se contragira para leerse derecho"""
    out = ['<g id="zonas-nombre" pointer-events="none" font-weight="800" text-anchor="middle" fill="#041E7E" fill-opacity=".62" '
           'stroke="#fff" stroke-opacity=".85" stroke-linejoin="round" paint-order="stroke">']
    for z in rotulos:
        px, py = fx1 - z["y"], z["x"] + y0              # pantalla -> plano
        giro = "" if z["vertical"] else f' transform="rotate(90 {px:.1f} {py:.1f})"'
        out.append(f'<text x="{px:.1f}" y="{py + z["size"] * .34:.1f}" font-size="{z["size"]}" stroke-width="{z["size"] * .22:.1f}"{giro}>{escape(z["nombre"])}</text>')
    out.append("</g>")
    return "".join(out)


def insertar(svg_lineas, grupos_pasillo, y0, fx1):
    """mete el grupo de rótulos justo antes de las etiquetas (bajo ellas, sobre las góndolas y el color por familia)"""
    txt = "\n".join(svg_lineas)
    ini = txt.find('<g id="etiquetas">')
    if ini < 0: return svg_lineas
    cajas = [tuple(float(v) for v in m.split()) for m in re.findall(r'data-b="([^"]+)"', txt[ini:])]
    if "capa" not in _CACHE: _CACHE["capa"] = svg_zonas(zonas(grupos_pasillo, cajas, y0, fx1), y0, fx1)  # los rótulos no cambian con la ruta
    capa = _CACHE["capa"]
    if "bordes" not in _CACHE: _CACHE["bordes"] = svg_bordes(grupos_pasillo)
    ini2 = txt.find('<g id="modulos">')
    if ini2 >= 0 and ini2 < ini:
        txt = txt[:ini2] + _CACHE["bordes"] + chr(10) + txt[ini2:]
        ini = txt.find('<g id="etiquetas">')
    return (txt[:ini] + capa + "\n" + txt[ini:]).split("\n")
