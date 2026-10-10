"""Regenera todo lo que usa la app (data/) y los fixtures de paridad: PDF + XLSX -> plano, catálogo público, cuadrícula.
Requiere en pipeline/fuentes/: «Calle 80 con puntas 2.pdf» y «Ubicación de Productos Calle 80 1.xlsx» (este no se sube al repositorio)."""
import os, subprocess, sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
PASOS = [
    ("extraer_pdf.py", {}), ("clasificar.py", {}), ("catalogo.py", {}), ("familias.py", {}),
    ("ruta.py", {"RUTA_EXPORTAR": "1"}),   # cuadrícula, anclas y obstáculos
    ("ruta.py", {"RUTA_TODOS": "1"}),      # rutas de referencia (67 destinos)
    ("ruta.py", {}),                       # casos de prueba (incluye las 8 caras sin ancla)
    ("exportar_datos.py", {}),
]
for script, extra in PASOS:
    print(f"==> {script} {extra or ''}", flush=True)
    args = [sys.executable, "-I", script] + (["5"] if script == "ruta.py" else [])
    r = subprocess.run(args, cwd=RAIZ, env={**os.environ, "PYTHONIOENCODING": "utf-8", **extra}, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-2000:]); sys.exit(f"falló {script}")
print("listo: data/ y tests/fixtures/ regenerados")
