"""Fase 7 - buscador de productos de 1 a 4 palabras, sin dependencias externas.
Misma lógica que el JavaScript de la página demo (scripts/buscador.js); salidas/paridad se prueba con node."""
import re, unicodedata, collections

PESO = (("d", 3.0), ("c", 2.0), ("f", 1.0))          # descripción > conjunto > familia
STOP = {"de", "del", "la", "el", "los", "las", "y", "para", "con", "en", "un", "una", "por", "al"}
ALIAS = {"galon": "gl", "galones": "gl", "gal": "gl", "litro": "lt", "litros": "lt", "lts": "lt", "kilo": "kg", "kilos": "kg",
         "kgs": "kg", "metro": "mt", "metros": "mt", "mts": "mt", "pulgada": "in", "pulgadas": "in", "pulg": "in",
         "unidad": "und", "unidades": "und", "uds": "und", "cms": "cm", "mms": "mm"}
SINONIMOS = [["bombillo", "bombilla", "foco"], ["destornillador", "desarmador"], ["inodoro", "sanitario", "taza"], ["grifo", "llave"],
             ["lavaplato", "lavadero", "fregadero"], ["ducha", "regadera"], ["tubo", "tuberia"], ["trapero", "mopa"],
             ["clavo", "puntilla"], ["cinta", "teipe", "tape"], ["nevera", "refrigerador"], ["televisor", "tv", "television"],
             ["pintura", "vinilo"], ["blanco", "blanca"], ["negro", "negra"], ["martillo", "mazo"], ["candado", "cerrojo"],
             ["cerradura", "chapa"], ["pegante", "pegamento", "adhesivo"], ["silicona", "silicon"], ["ventilador", "abanico"],
             ["lampara", "luminaria"], ["interruptor", "switch", "suiche"], ["tomacorriente", "toma"]]
TOKEN = re.compile(r"\d+(?:[./]\d+)+|[a-z0-9]+")


def normalizar(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _stem(t):
    if len(t) > 4 and t.endswith("s") and not t.endswith("ss") and not any(c.isdigit() for c in t):
        return t[:-1]
    return t


def tokens(s):
    return [_stem(ALIAS.get(t, t)) for t in TOKEN.findall(normalizar(s))]


_SIN = {}
for g in SINONIMOS:
    gs = [_stem(x) for x in g]
    for x in gs: _SIN[x] = [y for y in gs if y != x]


def dl(a, b, k):
    """distancia de edición con transposición (OSA); corta si supera k"""
    if abs(len(a) - len(b)) > k: return k + 1
    prev2, prev = None, list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            c = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + c)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        if min(cur) > k: return k + 1
        prev2, prev = prev, cur
    return prev[-1]


class Indice:
    def __init__(self, productos):
        """productos: lista de dict(sku, desc, conjunto, familia, ubic=[{pasillo, id_plano}])"""
        self.p = productos
        self.t = []                       # tokens por producto y campo
        self.vocab = collections.Counter()
        self.post = collections.defaultdict(list)
        for i, pr in enumerate(productos):
            d, c, f = tokens(pr["desc"]), tokens(pr["conjunto"]), tokens(pr["familia"])
            self.t.append({"d": d, "c": c, "f": f})
            for tk in set(d + c + f):
                self.vocab[tk] += 1; self.post[tk].append(i)
        self.inicios = collections.Counter(t['d'][0] for t in self.t if t['d'] and not any(ch.isdigit() for ch in t['d'][0]))
        self.por_largo = collections.defaultdict(list)
        for tk in self.vocab: self.por_largo[len(tk)].append(tk)
        self.sku = {}
        for i, pr in enumerate(productos): self.sku.setdefault(pr["sku"], i)
        self.sku0 = {}
        for i, pr in enumerate(productos): self.sku0.setdefault(pr["sku"].lstrip("0"), []).append(i)

    # ---- expansión de una palabra de la búsqueda a términos del vocabulario con su calidad
    def expandir(self, q):
        out = {}
        def poner(v, w):
            if w > out.get(v, 0): out[v] = w
        if q in self.vocab: poner(q, 1.0)
        for s in _SIN.get(q, []):
            if s in self.vocab: poner(s, 0.9)
        if any(c.isdigit() for c in q): return out         # medidas y números: solo coincidencia exacta
        if len(q) >= 3:
            for v in self.vocab:
                if v != q and v.startswith(q): poner(v, 0.8)
        if len(q) >= 4:
            k = 1 if len(q) <= 6 else 2
            for L in range(len(q) - k, len(q) + k + 1):
                for v in self.por_largo.get(L, ()):
                    if v == q or any(ch.isdigit() for ch in v): continue
                    d = dl(q, v, k)
                    if d <= k: poner(v, 0.6 if d == 1 else 0.5)
        return out

    def _puntuar(self, i, exps):
        t = self.t[i]; ts = []; pos = []
        for e in exps:
            best = 0.0
            for f, fw in PESO:
                q = max((e.get(x, 0) for x in t[f]), default=0)
                if q * fw > best: best = q * fw
            ts.append(best)
            pos.append({j for j, x in enumerate(t["d"]) if e.get(x, 0) > 0})
        bonus = sum(1.0 for a in range(len(exps) - 1) if any((j + 1) in pos[a + 1] for j in pos[a]))
        if pos and 0 in pos[0]: bonus += 0.5
        return sum(1 for x in ts if x > 0), sum(ts) + bonus

    def buscar(self, texto, k=5):
        toks = tokens(texto)
        # SKU exacto
        if len(toks) == 1 and toks[0].isdigit():
            if toks[0] in self.sku: return dict(idx=[self.sku[toks[0]]], tipo="sku", sugerencias=[])
            alt = self.sku0.get(toks[0].lstrip("0"), [])
            if alt: return dict(idx=alt[:k], tipo="sku", sugerencias=[])
        q = [x for x in toks if x not in STOP] or toks
        q = q[:4]
        if not q: return dict(idx=[], tipo="vacio", sugerencias=[])
        exps = [self.expandir(x) for x in q]
        cand = set()
        for e in exps:
            for v in e: cand.update(self.post[v])
        sc = [(i,) + self._puntuar(i, exps) for i in cand]
        if not sc: return dict(idx=[], tipo="sin_resultados", sugerencias=self.sugerir(q, exps))
        mx = max(s[1] for s in sc)
        sc = [s for s in sc if s[1] == mx]
        sc.sort(key=lambda s: (-s[2], len(self.t[s[0]]["d"]), s[0]))
        return dict(idx=[s[0] for s in sc[:k]], tipo="todas" if mx == len(q) else "parcial", sugerencias=[])

    def sugerir(self, q, exps, n=3):
        """3 búsquedas parecidas: palabra por palabra, el término más cercano y frecuente del catálogo"""
        cands = []
        for x, e in zip(q, exps):
            c = []
            if e: c.append((0, -self.vocab[max(e, key=lambda v: (e[v], self.vocab[v]))], max(e, key=lambda v: (e[v], self.vocab[v]))))
            else:
                for L in range(max(2, len(x) - 3), len(x) + 4):
                    for v in self.por_largo.get(L, ()):
                        if any(ch.isdigit() for ch in v): continue
                        d = dl(x, v, 2)
                        if d <= 2 or (len(x) >= 3 and v.startswith(x[:3])): c.append((min(d, 4), -self.vocab[v], v))
            cands.append(sorted(set(c))[:n])
        sug = []
        for r in range(n):
            partes = []
            for x, c in zip(q, cands):
                partes.append(c[min(r, len(c) - 1)][2] if c else x)
            s = " ".join(partes)
            if s not in sug and s != " ".join(q): sug.append(s)
        if not sug: sug = [w for w, _ in [(w, c) for w, c in self.inicios.most_common(30) if len(w) >= 4][:n]]  # nada parecido: lo más buscable del catálogo
        return sug[:n]

    def resultado(self, i):
        pr = self.p[i]; ub = pr["ubic"]
        vistos, orden = set(), []
        for u in ub:
            if u["pasillo"] not in vistos: vistos.add(u["pasillo"]); orden.append(u)
        elegido = next((u for u in orden if u["id_plano"]), None)   # primera ubicación con pasillo en el plano
        alternativas = [u["pasillo"].upper() or "(sin pasillo)" for u in orden if u is not elegido]
        return dict(sku=pr["sku"], descripcion=pr["desc"], conjunto=pr["conjunto"], familia=pr["familia"],
                    pasillo=(elegido["pasillo"].upper() if elegido else (orden[0]["pasillo"].upper() if orden and orden[0]["pasillo"] else "")),
                    id_plano=elegido["id_plano"] if elegido else None, alternativas=alternativas,
                    primera_ubicacion_en_plano=bool(orden and orden[0]["id_plano"]))
