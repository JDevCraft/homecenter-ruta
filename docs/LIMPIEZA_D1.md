# Bloque D1 · código y archivos sin uso (pendiente de aprobación)

Fuentes: knip (TS/JS), vulture (pipeline/), revisión de carpetas. **Nada se ha borrado.**

| Archivo / carpeta | Motivo | Acción propuesta |
|---|---|---|
| `public/file.svg`, `globe.svg`, `next.svg`, `vercel.svg`, `window.svg` | Restos de create-next-app; ninguna página los usa | Borrar |
| `tests/e2e/movil.mjs` (knip: sin uso) | Script manual con Chrome/CDP; no lo importa nada, se corre con `node` | Conservar; añadirlo a `entry` de knip |
| `PAUSA` en `lib/animacion/linea-de-tiempo.ts:3` | Export sin importadores externos | Quitar `export`, conservar constante |
| `origenEntrada` en `lib/ruta/calcular.ts:157` y `lib/ruta/index.ts:1` | Sin uso (la UI no usa rutas `desde`) | Conservar: parte de la API de rutas desde otro pasillo |
| Tipos `ElementosRuta`, `Segmento`, `RefPython` | Exportados sin importadores | Quitar `export` |
| Tipos `RespuestaBusqueda`, `Resultado` (buscador) | Tipos públicos del buscador | Conservar |
| `pipeline/mapa_cliente.py:328` `hito_entrada` (100 %) | Variable asignada y nunca leída | Borrar |
| `pipeline/mapa_cliente.py:19` `MAP_W`, `:36` `HITO_NOMBRE` | Constantes sin uso | Borrar |
| `pipeline/mapa_cliente.py:314` `leyenda_categorias`, `:478` `fin_por_giros` | Funciones sin llamadas | Borrar tras confirmar que `exportar_datos.py` no las usa |
| `pipeline/catalogo.py:97` `sp`; `:80` `cargar` | Sin uso aparente | Borrar `sp`; `cargar` revisar antes |
| `pipeline/buscador.py:111` `qn`, `pipeline/ruta.py:332` `t_ini` | Variables sin uso | Borrar |
| `pipeline/reporte_sin_mapa.py` (vulture: `title`, `font`, `alignment`…) | Falsos positivos de openpyxl | Conservar |
| `pipeline/__pycache__/`, `tests/**/__pycache__` | Ya ignorados por git; basura local | Borrar del disco |
| `pipeline/salidas/` | Regenerable con `npm run datos`, ignorado por git | Conservar localmente |
| `pipeline/fuentes/Calle 80 con puntas 2.pdf` (287 KB, versionado) | Plano de la tienda, necesario para regenerar | Conservar (Juan decide si va al repo privado) |
| `AGENTS.md` | Nota de create-next-app | Conservar |
| Proyecto `POC Ubicaciones` (≈1.200 archivos en `out/`) | Fuera de este repo | **No se toca** |

## Revisión de datos privados (D2)

- `.gitignore` cubre `*.xlsx`, `pipeline/fuentes/*.xlsx`, `pipeline/salidas/`, `out/`, `out-e2e/`, `/node_modules`, `/.next/`. Verificado.
- Historial (`git log --all`, 3 commits): **ningún** xlsx/csv/out/out-e2e/perfil de Chrome en ningún commit.
- Búsqueda de `costo|cantidad|inventario|reposici` en todos los commits: solo comentarios, README, `.gitignore` y pruebas que verifican su ausencia. Ningún dato.
- `data/catalogo.json` (2,6 MB): claves `c`, `f`, `p`; fila = SKU, descripción, conjunto, familia, pasillos. Sin campos privados (regex sobre el JSON completo).
- Resultado: **historial limpio, no hace falta reescribirlo.**
