# Pipeline de datos (Python, solo offline)

Python regenera los datos que usa la app; la app desplegada **no depende de Python**.

```
fuentes/Calle 80 con puntas 2.pdf  ──extraer_pdf.py──▶ salidas/extraccion_cruda.json
                                   ──clasificar.py (+ correcciones.json)──▶ salidas/tienda_42.json
fuentes/Ubicación de Productos…xlsx ──catalogo.py──▶ salidas/catalogo.json (todavía con UBICACION)
                                   ──familias.py (+ categorias_familia.json)──▶ salidas/categoria_por_pasillo.json
ruta.py (RUTA_EXPORTAR / RUTA_TODOS) ──▶ cuadrícula, anclas, obstáculos y rutas de referencia
exportar_datos.py ──▶ ../data/*.json (públicos) y ../tests/fixtures/*.json (paridad)
```

## Regenerar todo
```bash
pip install -r pipeline/requirements.txt
# poner el XLSX original en pipeline/fuentes/ (no se sube al repositorio: trae costos y cantidades)
npm run datos        # = python pipeline/generar_todo.py
npm test && npm run paridad
```

## Qué se versiona y qué no
- Se versiona `data/` (plano, cuadrícula, catálogo **público**) y `tests/fixtures/`.
- No se versionan `pipeline/salidas/` ni ningún `*.xlsx`.
- El catálogo público solo lleva SKU, descripción, conjunto, familia y pasillos. COSTO TOTAL, CANTIDAD, TIPO_INVENTARIO,
  TIPO REPOSICION y UBICACION no salen de `pipeline/`.

## Correcciones manuales
`correcciones.json` (nunca se edita el JSON generado): obstáculos que el PDF no trae (`agregar_obstaculo`), cierre de módulos por zona
(`cierre_modulos`: `modulos_columna_derecha`, `modulos_fila_zona_c` con `transitable`), vía obligada del pasillo central (`ruta_via`)
y los cruces pendientes de confirmar en tienda (`cruces_columna_derecha`).

## Referencia
`ruta.py`, `buscador.py` y `mapa_cliente.py` son la implementación de referencia en Python. La app usa el port en TypeScript
(`lib/ruta`, `lib/buscador`); `tests/` comprueba que ambos dan lo mismo.
