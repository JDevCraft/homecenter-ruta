"""Fase 4: superposición de tienda_42.json sobre el PDF -> salidas/validacion.png + recortes por zona + criterios."""
import json, pymupdf
SC = 1.5
t = json.load(open("salidas/tienda_42.json", encoding="utf-8"))
src = pymupdf.open("fuentes/Calle 80 con puntas 2.pdf")[0]
W, H = src.rect.width, src.rect.height
# fondo como imagen en una página limpia: dibujar sobre el PDF original contamina el estado gráfico (contorno verde)
doc = pymupdf.open(); pg = doc.new_page(width=W, height=H)
pg.insert_image(pg.rect, pixmap=src.get_pixmap(matrix=pymupdf.Matrix(SC, SC)))
COL = {"mueble": (0, .55, 0), "hito": (.6, 0, .8), "sin_clasificar": (1, .45, 0), "cabecera": (0, .45, .9),
       "continuacion": (0, .6, .6)}
def box(b, c, w=2): pg.draw_rect(pymupdf.Rect(*b), color=c, width=w)
for m in t["muebles"]:
    box(m["bbox"], COL[m["tipo"]], 1.5 if m["tipo"] == "cabecera" else 2.5)
    b = m["bbox"]
    if m["tipo"] == "cabecera": continue
    sc = m["tipo"] == "sin_clasificar"
    pg.insert_text((b[0] + 3, b[1] + 28 if sc else b[1] + 14), m["id"], fontsize=9 if sc else 13,
                   color=(.85, 0, 0) if sc else (0, 0, .7))
for b in t["bloques_modulos"]: box(b["bbox"], (.9, 0, .6), 1.5)
for h in t["huerfanos"]: box(h["bbox"], (1, 0, 0), 4)
for b in t["postes_entrada"]: box(b, (0, 0, 0), 3)
for h in t["hitos"]: pg.draw_circle(h["pos"], 5, color=(.6, 0, .8), fill=(.6, 0, .8))
# leyenda
LEG = [("mueble con ID", "mueble"), ("hito / zona", "hito"), ("cabecera (atributo)", "cabecera"),
       ("continuación de fila (-E)", "continuacion"), ("sin clasificar", "sin_clasificar")]
x, y = 1500, 40
for i, (n, k) in enumerate(LEG):
    pg.draw_rect(pymupdf.Rect(x, y + i * 28, x + 30, y + i * 28 + 18), color=COL[k], width=3)
    pg.insert_text((x + 40, y + i * 28 + 14), n, fontsize=16, color=(0, 0, 0))
pg.draw_rect(pymupdf.Rect(x, y + 5 * 28, x + 30, y + 5 * 28 + 18), color=(.9, 0, .6), width=2)
pg.insert_text((x + 40, y + 5 * 28 + 14), "bloque de módulos", fontsize=16, color=(0, 0, 0))
render = lambda clip=None, s=1.0: pg.get_pixmap(matrix=pymupdf.Matrix(s, s), clip=clip)
render(s=1.0).save("salidas/validacion.png")
ZONAS = {"entrada": (40, 380, 800, 760), "norte": (40, 200, 1450, 620), "centro": (330, 600, 1300, 1260),
         "columna_derecha": (1230, 200, 2090, 1560), "zona_c": (250, 1080, 1300, 1560), "izquierda_sur": (40, 1000, 500, 1560)}
for n, c in ZONAS.items(): render(pymupdf.Rect(*c), 1.6).save(f"salidas/validacion_{n}.png")

ids = {e for m in t["muebles"] for e in m["etiquetas"]}
split = sorted(m["id"] for m in t["muebles"] if m["id"][-2:] in ("-N", "-S"))
print("IDs únicos:", len(ids), "(esperado 67) | muebles sin ID:", sum(not m["id"] for m in t["muebles"]))
print("tramos partidos:", split)
print("sin_clasificar:", [m["id"] for m in t["muebles"] if m["tipo"] == "sin_clasificar"])
print("huérfanos:", len(t["huerfanos"]))
