"""Fase 2: extracción cruda del PDF -> salidas/extraccion_cruda.json (sin interpretar)."""
import json, sys, pymupdf

pdf = sys.argv[1] if len(sys.argv) > 1 else "fuentes/Calle 80 con puntas 2.pdf"
out = sys.argv[2] if len(sys.argv) > 2 else "salidas/extraccion_cruda.json"
doc = pymupdf.open(pdf)
page = doc[0]
r = lambda v: round(v, 2)
rects, lines = [], []
for d in page.get_drawings():
    fill = d.get("fill"); stroke = d.get("color")
    for it in d["items"]:
        if it[0] == "re":
            x0, y0, x1, y1 = it[1]
            rects.append(dict(x0=r(x0), y0=r(y0), x1=r(x1), y1=r(y1), w=r(x1-x0), h=r(y1-y0),
                              fill=fill, stroke=stroke, width=d.get("width")))
        elif it[0] == "l":
            lines.append(dict(p1=[r(it[1].x), r(it[1].y)], p2=[r(it[2].x), r(it[2].y)],
                              stroke=stroke, width=d.get("width")))
words = [dict(x0=r(w[0]), y0=r(w[1]), x1=r(w[2]), y1=r(w[3]), text=w[4]) for w in page.get_text("words")]
json.dump(dict(page=dict(w=page.rect.width, h=page.rect.height), rects=rects, lines=lines, words=words),
          open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(rects), "rects", len(lines), "lines", len(words), "words")
page.get_pixmap(matrix=pymupdf.Matrix(0.8, 0.8)).save("salidas/plano.png")
