# CLAUDE.md — normas-obsidian

Monorepo: extractor Python (DAFP + Senado → notas Obsidian, consolidadas por
artículo) + biblioteca generada (32 normas) + catálogo + plugin de Obsidian
(versión publicada: 0.4.1). Todo el código, los comentarios, los mensajes y
la documentación van **en español**.

## Comandos

```bash
# Python: usar SIEMPRE el venv (el python3 del sistema no tiene bs4/pytest)
cd extractor
.venv/bin/pip install -e ".[dev]"       # si no existe: ~/anaconda3/bin/python -m venv .venv
.venv/bin/python -m pytest -q           # 58 pruebas, ~3 s
.venv/bin/normas-cli todas              # regenera biblioteca/ (HTML cacheado en ~/.cache/normas-obsidian/html)
.venv/bin/normas-cli verificar          # debe terminar en «✓ biblioteca sin errores»
.venv/bin/normas-cli catalogo           # regenera catalogo/ (después de cada `todas`)

# Plugin (lint = reglas del escáner de la tienda de Obsidian; también en la CI)
cd plugin-obsidian && npm ci && npm run lint && npm run build && npm test

# Comparar fuentes (DAFP vs Senado)
.venv/bin/normas-cli comparar CGP --salida /tmp/cgp.md

# E2E en Obsidian real (Obsidian del usuario CERRADO; usa configuración aislada)
export E2E_DIR=/tmp/normas-e2e
VAULT_ORIGEN=~/Documentos/Obsidian/adolfo-s-rey-b e2e/preparar.sh   # copia Derecho/ (solo lectura)
e2e/servir.sh &                      # catálogo local en http://127.0.0.1:8765/catalogo
e2e/obsidian.sh &                    # app aislada (XDG_CONFIG_HOME propio)
node e2e/run.mjs [escenario …]       # informe en $E2E_DIR/informe.md + capturas
# Contra GitHub: tras preparar.sh, data.json = {"destino":"Normas"} (sin urlBase)
# y, para probar lo publicado, el main.js del release en la carpeta del plugin.

# Release (tag sin «v»; release.yml adjunta main.js y manifest.json)
cd plugin-obsidian && npm version X.Y.Z --no-git-tag-version   # package, manifest, versions
git commit … && git push && (CI verde) && git tag -a X.Y.Z -m "…" && git push origin X.Y.Z
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
| `consolidar.py` | Une todas las fuentes de una norma: base estructural (Senado si cubre ≥95 %) y, por artículo, la versión con el evento de vigencia más reciente (reformas y sentencias C-). `todas`/`extraer` lo usan para toda norma registrada. |
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
  Obsidian). Tags de release sin «v» (`0.4.1`).
- `minAppVersion` es 1.6.6: APIs de Obsidian ≥ 1.13 (`setDestructive`,
  `getSettingDefinitions`…) solo con detección en tiempo de ejecución.
  `npm run lint` no admite desactivar `@typescript-eslint/no-deprecated`.
- Commits a nombre de `adolfo-s-rey-b` (email noreply de GitHub). Releases y envío
  a la tienda solo con confirmación directa del usuario.

## Tienda de Obsidian

- Desde mayo de 2026 el envío se hace en **community.obsidian.md** (cuenta de
  Obsidian del usuario + GitHub vinculado); `obsidianmd/obsidian-releases` es solo un
  espejo y **no acepta PRs**. Solo el usuario puede enviarlo.
- El portal lee `manifest.json` de `main` e instala desde el release con el mismo
  tag. Revisión automática (eslint-plugin-obsidianmd, malware, políticas) en cada
  versión; si falla, el plugin sale de la búsqueda en 24 h. *Preview scan* en el panel.
- La página del plugin en la tienda muestra el `README.md` de la raíz.

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
  norma. Ninguna fuente gana siempre: difieren artículo por artículo. Decisión del
  usuario: **toda norma se consolida desde todas las fuentes** (`consolidar.py`);
  nunca publicar una norma de una sola fuente si hay otra disponible.
- Decretos únicos (1082/2015, 2555/2010) usan numeración punteada `2.2.1.1.1.1.1`
  y niveles hasta SUBSECCIÓN; solo están en el DAFP.
- Senado: marcas «<Artículo modificado por…>» pueden abarcar varios nodos HTML; la
  fecha puede ir dentro de la identidad («Ley 2445 de 11 de febrero de 2025»).

## Pruebas E2E (aprendido)

- VS Code exporta `ELECTRON_RUN_AS_NODE=1`: Obsidian/su CLI fallan con
  «Cannot find module 'electron'». `e2e/obsidian.sh` lo elimina.
- El CLI se conecta a la instancia en ejecución: con el Obsidian del usuario
  abierto, los comandos podrían caer en su vault real (con Sync). Mantenerlo cerrado.
- `obsidian eval` **no espera** promesas largas: lanzar la tarea y sondear
  (`tarea()` en `e2e/run.mjs`). Nunca lanzar descargas en paralelo desde eval.
- Bóveda nueva: Obsidian muestra «¿Confía en el autor de esta bóveda?» (o abre
  Preferencias) y no carga complementos hasta aceptarlo: `run.mjs` lo acepta
  (`activarComplementos`).
- Arrancar **primero la app** y esperar a que `e2e/obsidian.sh version` responda: si
  se invoca el CLI sin app abierta, sus clientes (también procesos Electron)
  retienen el bloqueo de instancia única y la app ya no arranca (bloqueo mutuo).
- Para cerrar la instancia de pruebas, matar el PID de
  `/usr/lib/electron43/electron /usr/lib/obsidian/app.asar` (no usar `pkill -f`
  ni `pgrep -f … | kill` con patrones que aparezcan en el propio comando: matan el shell).
- Con la biblioteca completa (~18.000 notas) Obsidian tarda minutos en indexar y el
  CLI responde vacío mientras tanto: `run.mjs` reintenta (`jsJSON`, `contarNotas`).
  Un resultado vacío de `eval` se imprime como «=>» a secas.
- `dev:screenshot` puede devolver un fotograma viejo si la ventana no está visible:
  verificar por el DOM (`dev:dom`, `eval`) además de la captura.

## Fixtures

Ver `extractor/tests/README.md`. Los extractos se generan con
`tests/recortar_fixture.py` desde la caché.
