# Homecenter Calle 80 · buscador y ruta en tienda

Demo para el cliente en el celular: busca un producto, muestra en qué pasillo está y dibuja (animada) la ruta desde la entrada.
Next.js (App Router) + TypeScript. El mapa es un SVG renderizado por React, sin librerías de mapas.

## Cómo funciona

- **Ruta:** `calcularRuta()` (A\* sobre una cuadrícula ya construida) corre en el celular. Datos en `data/`.
- **Búsqueda:** el catálogo (39.042 SKU) **no** se descarga al celular; vive en memoria del servidor y se consulta con `GET /api/buscar?q=…` (máx. 5 resultados, solo campos públicos).
- **Python** queda fuera de línea, en `pipeline/` (extrae el PDF del plano, clasifica, valida y exporta los JSON de `data/`).

## Correr en local

```bash
npm install
npm run dev          # http://localhost:3000
npm test             # 66 pruebas (paridad de rutas y buscador con Python, /api/buscar)
npm run typecheck && npm run lint
npm run build && npm run start
```

## Abrirlo desde el celular (misma wifi)

1. `npm run dev -- -H 0.0.0.0`
2. Mira la IP del PC con `ipconfig` (IPv4 de la wifi).
3. En el celular: `http://<IP>:3000`.
4. Si no carga, permite Node.js en el Firewall de Windows para redes privadas.

## Regenerar los datos (`npm run datos`)

Necesita Python 3 con `pip install -r pipeline/requirements.txt` (pymupdf, shapely, numpy, openpyxl).

1. Pon el XLSX del catálogo en `pipeline/fuentes/` (**nunca se sube**: trae costos y cantidades; está en `.gitignore`).
2. `npm run datos` regenera `data/*.json` y los fixtures de `tests/fixtures/`.
3. `npm test` y `npm run paridad` (escribe `docs/paridad_rutas.md`) confirman que nada cambió.

El catálogo público solo lleva SKU, descripción, conjunto, familia y pasillos. COSTO TOTAL, CANTIDAD, TIPO_INVENTARIO,
TIPO REPOSICION y UBICACION no salen de `pipeline/`; hay pruebas que lo verifican.

## Ajustes: `pipeline/correcciones.json`

Después de editarlo, corre `npm run datos`.

| id | acción | efecto |
|---|---|---|
| `cubos-entrada` | `agregar_obstaculo` | Agrega un obstáculo (bbox) que el PDF no trae: los 2 cubos junto a la entrada. Las rutas lo rodean. |
| `modulos_columna_derecha` | `cierre_modulos` (`cierre: 0`) | En esa región los módulos de la columna derecha (frente a 29a–39a) se tratan como independientes: no se cierran los huecos de 10 pt entre ellos, así que se puede cruzar. |
| `modulos_fila_zona_c` | `cierre_modulos` (`cierre: 0`) | Igual, para la fila de 21 módulos sobre las góndolas 10c–21c. |
| `cruces_columna_derecha` | informativo | Lista los 3 cruces por validar (y≈557, 632, 707). No cambia rutas. |
| `inicio_pasillo_central` | `ruta_via` | Los destinos 09c–21c pasan obligatoriamente por (506,8; 1131,7), el inicio del pasillo central de la zona c. Cambiar `pos` mueve ese punto; `destinos` define a quién aplica. |

Parámetros fijos aprobados (en `pipeline/ruta.py` y `lib/ruta/`): margen del carrito 5 pt, celda 5 pt, cierre de módulos 10 pt.
Si se cambian, hay que regenerar datos y revisar la paridad.

`lib/config.ts` tiene dos interruptores de la interfaz: `MOSTRAR_INDICACIONES` (tarjeta «Paso N de M») y `MOSTRAR_CONTROLES`
(Paso anterior / Repetir ruta / Paso siguiente). Hoy están en `false`, como pidió Juan; poner `true` los activa.

## Supuestos sin validar en tienda

- Los **3 cruces de la columna derecha** (y≈557, 632, 707): huecos de 12 pt con 2 pt libres tras el margen; la ruta puede pasar por ahí.
- Los **huecos de la fila de módulos de la zona c** (10c–21c): se asumió que cada módulo es independiente y se puede pasar entre ellos.
- Los **pasillos fuera del plano**: 7.373 SKU (102 pasillos, incluido vacío) no están en el plano. La app solo avisa
  «Este producto está en una zona fuera del plano»; no hay ruta.

## Limitaciones

- La **cara de la góndola** se elige por cercanía a la entrada porque el catálogo no la trae; si esa cara no tiene punto de acercamiento se usa la contraria y se marca «Lado contrario».
- **No hay metros, distancias ni tiempos** en ninguna parte de la interfaz.
- La ruta siempre sale de la entrada. La función para calcular desde otro pasillo existe (`desde`) pero la interfaz no la usa.

## Desplegar en Vercel (preview)

1. Repositorio **privado** en GitHub (lo crea y conecta Juan).
2. En Vercel: *Add New → Project →* importar el repo. Framework: Next.js (detección automática; sin ajustes).
3. **Sin variables de entorno.** No hay secretos; si algún día aparece una, documentarla aquí y nunca subirla.
4. *Settings → Deployment Protection*: dejar activa la protección (Vercel Authentication) para que los previews no sean públicos.
5. Cada rama/PR genera un preview. No se asigna dominio ni se despliega a producción hasta que Juan lo decida.

## Estructura

```
app/            páginas y Route Handler /api/buscar
components/     AppRuta, Mapa (SVG + cámara), MapaBase, Pill
lib/ruta/       cuadrícula, A*, suavizado, instrucciones
lib/buscador/   normalización, índice, catálogo
lib/animacion/  geometría, línea de tiempo, cámara, animador
data/           JSON generados por el pipeline (catálogo público, grid, obstáculos, mapa…)
pipeline/       Python fuera de línea (ver pipeline/README.md)
tests/          Vitest (+ e2e/movil.mjs con Chrome emulando móvil)
```
