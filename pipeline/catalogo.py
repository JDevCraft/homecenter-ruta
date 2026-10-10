"""Fase 7 - carga del catálogo real (XLSX) y cruce con los pasillos del plano.
Salidas: salidas/catalogo.json (solo campos permitidos + UBICACION como dato) y salidas/pasillos_sin_mapa.csv.
No se guardan ni se muestran COSTO TOTAL, CANTIDAD, TIPO_INVENTARIO ni TIPO REPOSICION."""
import csv, glob, json, os, sys, collections
import openpyxl

RAIZ = os.path.dirname(os.path.abspath(__file__))
XLSX = glob.glob(os.path.join(RAIZ, "fuentes", "Ubicaci*n de Productos Calle 80 1.xlsx"))
CAT_JSON = os.path.join(RAIZ, "salidas", "catalogo.json")
CSV_SIN_MAPA = os.path.join(RAIZ, "salidas", "pasillos_sin_mapa.csv")
# columnas que se leen; las demás (costo, cantidad, tipos) ni se cargan
NECESARIAS = ["UBICACION", "PASILLO", "SKU", "DESCRIPCION", "CODTIENDA", "CONJUNTO", "FAMILIA"]


def _txt(v):
    """todo como texto: SKU y SKU_TIENDA no pierden ceros a la izquierda (09715)"""
    if v is None: return ""
    if isinstance(v, float) and v.is_integer(): return str(int(v))
    return str(v).strip()


def leer_xlsx(ruta=None):
    ruta = ruta or XLSX[0]
    wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    filas = wb.active.iter_rows(values_only=True)
    cab = None
    for fila in filas:  # hay un título encima de los encabezados
        if fila and "UBICACION" in [str(c).strip() if c is not None else "" for c in fila]:
            cab = [str(c).strip() if c is not None else "" for c in fila]; break
    if cab is None: raise ValueError("no se encontró la fila de encabezados (UBICACION...)")
    ix = {c: cab.index(c) for c in NECESARIAS}
    out = []
    for fila in filas:
        if not fila or all(c is None or str(c).strip() == "" for c in fila): continue
        out.append({c: _txt(fila[i]) if i < len(fila) else "" for c, i in ix.items()})
    return out


def ids_del_plano():
    t = json.load(open(os.path.join(RAIZ, "salidas", "tienda_42.json"), encoding="utf-8"))
    return {e for m in t["muebles"] for e in m["etiquetas"]}


def resumen_previo(filas):
    """lo que se reporta ANTES de cargar: filas, CODTIENDA y PASILLO distintos"""
    cod = collections.Counter(f["CODTIENDA"] for f in filas)
    pas = collections.Counter(f["PASILLO"] for f in filas)
    return dict(filas=len(filas), codtienda=dict(cod), pasillos_distintos=len([p for p in pas if p]), pasillos_vacios=pas.get("", 0))


def construir(filas):
    plano = ids_del_plano()
    prods, orden = {}, []
    for f in filas:
        sku = f["SKU"]
        if sku not in prods:
            prods[sku] = dict(sku=sku, desc=f["DESCRIPCION"], conjunto=f["CONJUNTO"], familia=f["FAMILIA"], ubic=[])
            orden.append(sku)
        pas = f["PASILLO"].lower()
        # UBICACION se guarda como dato; la ruta usa solo PASILLO
        prods[sku]["ubic"].append(dict(ubicacion=f["UBICACION"], pasillo=pas, id_plano=pas if pas in plano else None))
    return [prods[s] for s in orden]


def reporte_sin_mapa(filas, productos):
    plano = ids_del_plano()
    filas_por, skus_por = collections.Counter(), collections.defaultdict(set)
    for f in filas:
        p = f["PASILLO"].lower()
        if p not in plano:
            k = p or "(vacío)"
            filas_por[k] += 1; skus_por[k].add(f["SKU"])
    with open(CSV_SIN_MAPA, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh); w.writerow(["pasillo", "filas", "productos_distintos"])
        for k, n in sorted(filas_por.items(), key=lambda kv: -len(skus_por[kv[0]])):
            w.writerow([k, n, len(skus_por[k])])
    return filas_por, skus_por


def cargar(forzar=False):
    if not forzar and os.path.exists(CAT_JSON) and os.path.getmtime(CAT_JSON) > os.path.getmtime(XLSX[0]):
        return json.load(open(CAT_JSON, encoding="utf-8"))
    filas = leer_xlsx()
    productos = construir(filas)
    json.dump(productos, open(CAT_JSON, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    reporte_sin_mapa(filas, productos)
    return productos


if __name__ == "__main__":
    filas = leer_xlsx()
    print("ANTES DE CARGAR:", json.dumps(resumen_previo(filas), ensure_ascii=False))
    cods = {f["CODTIENDA"] for f in filas}
    if len(cods) > 1: print("AVISO: CODTIENDA tiene más de un valor; no se filtra:", cods)
    productos = construir(filas)
    json.dump(productos, open(CAT_JSON, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    fp, _ = reporte_sin_mapa(filas, productos)
    con = sum(1 for p in productos if any(u["id_plano"] for u in p["ubic"]))
    prim = sum(1 for p in productos if p["ubic"][0]["id_plano"])
    multi = sum(1 for p in productos if len(p["ubic"]) > 1)
    print(f"productos (SKU distintos): {len(productos)} | con algún pasillo en el plano: {con} | sin ninguno: {len(productos) - con}")
    print(f"primera ubicación en el plano: {prim} | SKU con varias ubicaciones: {multi}")
    print(f"filas sin pasillo en el plano: {sum(fp.values())} en {len(fp)} pasillos distintos -> {CSV_SIN_MAPA}")
    plano = ids_del_plano(); usados = {u["id_plano"] for p in productos for u in p["ubic"] if u["id_plano"]}
    print(f"IDs del plano: {len(plano)} | con productos: {len(usados)} | sin productos: {sorted(plano - usados)}")
