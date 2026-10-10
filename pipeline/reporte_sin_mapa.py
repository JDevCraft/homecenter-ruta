"""Reporte para Juan: productos cuyo pasillo no existe en tienda_42.json -> salidas/productos_sin_mapa.xlsx
Solo lee salidas/catalogo.json y el plano; no cambia el buscador, el catálogo cargado ni las rutas."""
import collections, json, os
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

RAIZ = os.path.dirname(os.path.abspath(__file__))
os.chdir(RAIZ)
prods = json.load(open("salidas/catalogo.json", encoding="utf-8"))
tienda = json.load(open("salidas/tienda_42.json", encoding="utf-8"))
PLANO = sorted({e for m in tienda["muebles"] for e in m["etiquetas"]})

# --- agrupar por pasillo sin plano (el código tal como viene: en mayúsculas)
skus = collections.defaultdict(dict)       # pasillo -> {sku: producto}
filas = collections.Counter()
solo_ahi = collections.defaultdict(set)    # SKU cuyas ubicaciones NO están en el plano en absoluto
sin_ninguno = 0
for p in prods:
    sin = [u for u in p["ubic"] if not u["id_plano"]]
    if len(sin) == len(p["ubic"]): sin_ninguno += 1
    for u in sin:
        k = u["pasillo"].upper() or "(vacío)"
        filas[k] += 1; skus[k].setdefault(p["sku"], p)
        if len(sin) == len(p["ubic"]): solo_ahi[k].add(p["sku"])
orden = sorted(skus, key=lambda k: (-len(skus[k]), k))

def ejemplos(k, n=5):
    """hasta 5 ejemplos de conjuntos distintos (los más frecuentes primero), para ver de qué zona se trata"""
    ps = list(skus[k].values())
    cuenta = collections.Counter(p["conjunto"] for p in ps)
    out, usados = [], set()
    for conj, _ in cuenta.most_common():
        p = next(x for x in ps if x["conjunto"] == conj and x["sku"] not in usados)
        out.append(p); usados.add(p["sku"])
        if len(out) == n: return out
    for p in ps:                                   # pocos conjuntos: completa con otros productos
        if p["sku"] not in usados and len(out) < n: out.append(p); usados.add(p["sku"])
    return out

def mismo_numero(k):
    num = k[:2] if k != "(vacío)" else ""
    return ", ".join(i for i in PLANO if num and i[:2] == num) or "—"

# --- libro
wb = Workbook()
AZUL = PatternFill("solid", fgColor="041E7E"); CLARO = PatternFill("solid", fgColor="EEF2F8")
cab = lambda c: (setattr(c, "font", Font(bold=True, color="FFFFFF")), setattr(c, "fill", AZUL), setattr(c, "alignment", Alignment(wrap_text=True, vertical="center")))
def ajustar(ws, anchos):
    for i, a in enumerate(anchos, 1): ws.column_dimensions[get_column_letter(i)].width = a

# Hoja 1: resumen
ws = wb.active; ws.title = "Resumen"
total_sku = len(prods)
tot_filas = sum(filas.values())
ws["A1"] = "Productos cuyo pasillo no existe en el plano (tienda_42.json)"; ws["A1"].font = Font(bold=True, size=14, color="041E7E")
datos = [("SKU distintos del catálogo", total_sku),
         ("SKU sin NINGÚN pasillo en el plano", sin_ninguno),
         ("  como % del catálogo", f"{100 * sin_ninguno / total_sku:.1f} %"),
         ("Filas del catálogo en pasillos sin plano", tot_filas),
         ("Pasillos distintos sin plano (incluye «(vacío)»)", len(orden)),
         ("  de ellos, códigos con nombre", len([k for k in orden if k != "(vacío)"])),
         ("  filas sin pasillo (vacío)", filas.get("(vacío)", 0)),
         ("Pasillos del plano (IDs visibles)", len(PLANO))]
for i, (a, b) in enumerate(datos, 3):
    ws.cell(i, 1, a); ws.cell(i, 2, b)
r0 = 3 + len(datos) + 1
ws.cell(r0, 1, "Los 10 pasillos sin plano con más productos").font = Font(bold=True, color="041E7E")
for j, h in enumerate(["PASILLO", "SKU distintos", "Filas", "IDs del plano con el mismo número"], 1): cab(ws.cell(r0 + 1, j, h))
for i, k in enumerate(orden[:10], r0 + 2):
    ws.cell(i, 1, k); ws.cell(i, 2, len(skus[k])); ws.cell(i, 3, filas[k]); ws.cell(i, 4, mismo_numero(k))
n = r0 + 13
notas = ["Cómo leer esto:",
         "• «SKU distintos» por pasillo cuenta productos con al menos una ubicación en ese pasillo; un SKU con varias ubicaciones sin plano suma en cada una, "
         "por eso la suma de los pasillos es mayor que el total de SKU sin ningún pasillo en el plano.",
         "• La columna «solo aquí» de la hoja Pasillos son los SKU que no tienen ninguna otra ubicación en el plano: esos son los que hoy no se pueden llevar a un pasillo.",
         "• «IDs del plano con el mismo número» es solo una pista para detectar diferencias de nombre (p. ej. 22C vs 22A); no se usa para ninguna ruta.",
         "• Decisión pendiente (Juan): ¿son zonas fuera del plano (bodega, patio, carga...) o hay un problema de nombres entre catálogo y plano?"]
for i, t in enumerate(notas, n): ws.cell(i, 1, t).alignment = Alignment(wrap_text=True, vertical="top"); ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=4)
for i in range(n + 1, n + len(notas)): ws.row_dimensions[i].height = 48
ajustar(ws, [52, 16, 12, 38])

# Hoja 2: una fila por pasillo (de mayor a menor)
w2 = wb.create_sheet("Pasillos")
enc = ["PASILLO", "SKU distintos", "SKU solo aquí (sin otra ubicación en el plano)", "Filas", "Familia principal", "IDs del plano con el mismo número"] + \
      [f"Ejemplo {i} (DESCRIPCION · CONJUNTO · FAMILIA)" for i in range(1, 6)]
for j, h in enumerate(enc, 1): cab(w2.cell(1, j, h))
for i, k in enumerate(orden, 2):
    fam = collections.Counter(p["familia"] for p in skus[k].values()).most_common(1)[0]
    vals = [k, len(skus[k]), len(solo_ahi[k]), filas[k], f"{fam[0]} ({fam[1]})", mismo_numero(k)]
    ex = ejemplos(k)
    vals += [f"{p['desc']} · {p['conjunto']} · {p['familia']}" for p in ex] + [""] * (5 - len(ex))
    for j, v in enumerate(vals, 1):
        c = w2.cell(i, j, v); c.alignment = Alignment(wrap_text=True, vertical="top")
        if i % 2 == 0: c.fill = CLARO
w2.freeze_panes = "B2"; ajustar(w2, [12, 12, 20, 9, 30, 22] + [52] * 5)

# Hoja 3: detalle largo (un ejemplo por fila) con las columnas pedidas
w3 = wb.create_sheet("Detalle")
for j, h in enumerate(["PASILLO", "SKU distintos en el pasillo", "SKU", "DESCRIPCION", "CONJUNTO", "FAMILIA"], 1): cab(w3.cell(1, j, h))
r = 2
for k in orden:
    for m, p in enumerate(ejemplos(k)):
        for j, v in enumerate([k, len(skus[k]) if m == 0 else None, p["sku"], p["desc"], p["conjunto"], p["familia"]], 1):
            c = w3.cell(r, j, v)
            if m == 0: c.font = Font(bold=True)
        r += 1
w3.freeze_panes = "A2"; w3.auto_filter.ref = f"A1:F{r - 1}"; ajustar(w3, [12, 14, 12, 52, 44, 30])
for ws_ in (w2, w3):
    for col in ("C",): pass
for row in w3.iter_rows(min_row=2, min_col=3, max_col=3):
    for c in row: c.number_format = "@"                                  # el SKU es texto: no pierde ceros
wb.save("salidas/productos_sin_mapa.xlsx")
print("salidas/productos_sin_mapa.xlsx", "| pasillos:", len(orden), "| SKU sin ningún pasillo en el plano:", sin_ninguno, "| top:", [(k, len(skus[k])) for k in orden[:10]])
