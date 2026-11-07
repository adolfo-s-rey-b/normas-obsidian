# CLAUDE.md — normas-obsidian

Monorepo: extractor Python (DAFP → notas Obsidian) + biblioteca generada +
catálogo + plugin de Obsidian. Todo el código, los comentarios, los mensajes y
la documentación van **en español**.

## Comandos

```bash
# Python: usar SIEMPRE el venv (el python3 del sistema no tiene bs4/pytest)
cd extractor
.venv/bin/pip install -e ".[dev]"       # si no existe: ~/anaconda3/bin/python -m venv .venv
.venv/bin/python -m pytest -q           # 48 pruebas, ~3 s
.venv/bin/normas-cli todas              # regenera biblioteca/ (HTML cacheado en ~/.cache/normas-obsidian/html)
.venv/bin/normas-cli verificar          # debe terminar en «✓ biblioteca sin errores»
.venv/bin/normas-cli catalogo           # regenera catalogo/ (después de cada `todas`)

# Plugin
cd plugin-obsidian && npm ci && npm run build && npm test

# Comparar fuentes (DAFP vs Senado)
.venv/bin/normas-cli comparar CGP --salida /tmp/cgp.md

# E2E en Obsidian real (Obsidian del usuario CERRADO; usa configuración aislada)
export E2E_DIR=/tmp/normas-e2e
VAULT_ORIGEN=~/Documentos/Obsidian/adolfo-s-rey-b e2e/preparar.sh   # copia Derecho/ (solo lectura)
e2e/servir.sh &                      # catálogo local en http://127.0.0.1:8765/catalogo
e2e/obsidian.sh &                    # app aislada (XDG_CONFIG_HOME propio)
node e2e/run.mjs [escenario …]       # informe en $E2E_DIR/informe.md + capturas
```

Flujo al cambiar el parser o el render: pytest → `todas` → `verificar` →
revisar a mano algunas notas → `catalogo` → commit de código y de datos por
separado.

## Arquitectura (`extractor/normas_cli/`)

| Módulo | Qué hace |
| --- | --- |
| `fetch.py` | Descarga con reintentos y caché. Completa la cadena TLS rota del DAFP vía AIA (nunca `verify=False`). |
| `parse.py` | HTML → `Norma`. Unidades (`p`, `table`, `li`), cabeceras con validación de secuencia, epígrafe por negrita, niveles, rubros, firmas, envoltura, series de transitorios, esquema del registry, inferencia del orden de niveles. |
| `model.py` | `Norma`, `Nivel`, `Articulo`, `Bloque`, `HrefRef`. |
| `links.py` | Motor de wikilinks: marcadores de norma, enumeraciones, texto citado («así:»). |
| `registry.py` | `registry.yaml`: normas, siglas, diccionario de códigos, `jerarquia`/`esquema`. Solo reescribe el YAML si cambió algo. |
| `render.py` | Árbol → carpetas/notas (raíz, índices, artículos), frontmatter, vigencia, escritura atómica. |
| `verificar.py` | QA de la biblioteca (duplicados, alias ambiguos, carpetas vacías, enlaces rotos). |
| `catalogo.py` | `catalogo/index.json` + un paquete JSON por norma para el plugin. |
| `senado.py` | Adaptador de la Secretaría del Senado (páginas `_prNNN`, recuadros en JS, `<S>` → `~~`), normaliza a HTML tipo DAFP. |
| `comparar.py` | Compara una norma DAFP vs Senado: texto por artículo y reformas citadas solo por cada fuente. |
| `cli.py` | Subcomandos `extraer` (por defecto), `todas`, `verificar`, `catalogo`, `comparar`. |

## Convenciones que no se deben romper

- Nombre de nota: `art. N <ETIQUETA>.md` (etiqueta = sigla o `Ley N de A`).
  Transitorios: `art. transitorio N CPol`, series posteriores
  `art. transitorio N (AL x de y) CPol` (decisión del usuario). La Constitución
  es `CPol` (notación del usuario), con alias `CN`.
- Los enlaces a normas no registradas usan `nombre_normalizado()`
  (`Decreto 1736 de 2012`, sin «Nacional/Ley»), para que resuelvan cuando la
  norma se agregue.
- El motor de enlaces es **conservador**: ante la duda, no enlazar.
- `render()` reemplaza la carpeta completa de la norma; se niega a pisar una
  carpeta que no tenga `<ETIQUETA>.md` o `art. INTRO *.md`.
- `manifest.json`/`versions.json` viven en la raíz (requisito de la tienda de
  Obsidian). Tags de release sin «v» (`0.2.0`).

## Particularidades del DAFP (aprendidas a la mala)

- El Código Civil **no** está publicado (`i=39535` → «No disponible»): se toma del Senado.
- La CN no trae etiquetas «TÍTULO I/CAPÍTULO 1» → `esquema` en el registry.
- El CPT (Decreto 2158 de 1948, `i=5259`) está derogado por la Ley 2452 de 2025
  (`i=259639`, sigla CPTSS).
- El ET está envuelto por los arts. 1–4 del Decreto 624 de 1989 (envoltura).
- Fuente con errores: «de la 2195 de 2022» (falta «Ley»), `LIBRO SEXTO"`,
  dos artículos en un mismo `<p>`, «ARTICULOS 438.» como cabecera.
- No disfrazar el User-Agent: no hace falta y el entorno lo bloquea.
- La fecha «Última actualización» del Senado es de todo el sitio, no de cada
  norma; para saber cuál fuente es más reciente, mirar las reformas citadas
  (`comparar`). Ninguna fuente gana siempre: difieren artículo por artículo.

## Pruebas E2E (aprendido)

- VS Code exporta `ELECTRON_RUN_AS_NODE=1`: Obsidian/su CLI fallan con
  «Cannot find module 'electron'». `e2e/obsidian.sh` lo elimina.
- El CLI se conecta a la instancia en ejecución: con el Obsidian del usuario
  abierto, los comandos podrían caer en su vault real (con Sync). Mantenerlo cerrado.
- `obsidian eval` **no espera** promesas largas: lanzar la tarea y sondear
  (`tarea()` en `e2e/run.mjs`). Nunca lanzar descargas en paralelo desde eval.
- Para cerrar la instancia de pruebas, matar el PID de
  `/usr/lib/electron43/electron /usr/lib/obsidian/app.asar` (no usar `pkill -f`
  con ese patrón: coincide con el propio shell).

## Fixtures

Ver `extractor/tests/README.md`. Los extractos se generan con
`tests/recortar_fixture.py` desde la caché.
