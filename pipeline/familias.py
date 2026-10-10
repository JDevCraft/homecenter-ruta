"""Familia predominante por pasillo del plano y categoría de mapa.
Salidas: salidas/familia_por_pasillo.csv, salidas/familias_a_revisar.csv, salidas/categoria_por_pasillo.json (lo usa mapa_cliente).
Solo lee el catálogo cargado; no toca el buscador ni las rutas."""
import collections, csv, json, os
RAIZ = os.path.dirname(os.path.abspath(__file__))
os.chdir(RAIZ)
CFG = json.load(open("categorias_familia.json", encoding="utf-8"))
FAM_A_CAT = {f: c for c in CFG["categorias"] for f in c["familias"]}
REV = CFG["por_revisar"]

def clave_pasillo(i): return (int(i[:2]), i)            # 02a, 03a, 03c... en orden de plano

def calcular():
    prods = json.load(open("salidas/catalogo.json", encoding="utf-8"))
    por = collections.defaultdict(lambda: collections.defaultdict(set))   # pasillo -> familia -> SKU distintos
    for p in prods:
        for u in p["ubic"]:
            if u["id_plano"]: por[u["id_plano"]][p["familia"]].add(p["sku"])
    filas, info = [], {}
    for pas in sorted(por, key=clave_pasillo):
        cuentas = sorted(((len(s), f) for f, s in por[pas].items()), key=lambda x: (-x[0], x[1]))
        total = len({s for v in por[pas].values() for s in v})
        n1, f1 = cuentas[0]; n2, f2 = cuentas[1] if len(cuentas) > 1 else (0, "")
        # "mixto": la familia mayor no llega al 60 % de los SKU del pasillo, o la segunda tiene al menos la mitad de la primera
        mixto = n1 / total < 0.6 or (n1 and n2 / n1 >= 0.5)
        cat = FAM_A_CAT.get(f1)
        nombre, color = (cat["nombre"], cat["color"]) if cat else (REV["nombre"], REV["color"])
        filas.append(dict(pasillo=pas, familia_predominante=f1, categoria=nombre, sku_de_la_familia=n1, sku_total_pasillo=total,
                          participacion=f"{100 * n1 / total:.0f} %", mixto="mixto" if mixto else "", segunda_familia=f2, sku_segunda_familia=n2))
        info[pas] = dict(categoria=nombre, color=color, familia=f1, mixto=bool(mixto))
    return prods, por, filas, info

def main():
    prods, por, filas, info = calcular()
    with open("salidas/familia_por_pasillo.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0])); w.writeheader(); w.writerows(filas)
    json.dump(info, open("salidas/categoria_por_pasillo.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # familias: a qué categoría van, cuántos SKU hay en el plano y en qué pasillos predominan
    sku_fam = collections.Counter(); pred = collections.defaultdict(list)
    for pas, v in por.items():
        for f, s in v.items(): sku_fam[f] += len(s)
    for r in filas: pred[r["familia_predominante"]].append(r["pasillo"])
    with open("salidas/familias_a_revisar.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh); w.writerow(["familia", "categoria_asignada", "sku_en_el_plano", "pasillos_donde_predomina", "revisar"])
        for f, n in sku_fam.most_common():
            cat = FAM_A_CAT.get(f)
            w.writerow([f or "(sin familia)", cat["nombre"] if cat else REV["nombre"], n, " ".join(pred.get(f, [])), "" if cat else "SIN CATEGORÍA"])
    sin = [f or "(sin familia)" for f in sku_fam if f not in FAM_A_CAT]
    cuenta = collections.Counter(r["categoria"] for r in filas)
    print("pasillos:", len(filas), "| mixtos:", sum(1 for r in filas if r["mixto"]))
    print("pasillos por categoría:", dict(cuenta))
    print("familias sin categoría (a revisar):", sin)
    return filas

if __name__ == "__main__":
    main()
