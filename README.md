# Normas Colombianas → Obsidian

Convierte normativa colombiana (códigos, leyes y decretos) en notas de
[Obsidian](https://obsidian.md):

- **Un artículo por nota** (`art. 22 CGP.md`), con epígrafe, numerales,
  literales, parágrafos y tablas.
- **La jerarquía** de la norma (Libros, Partes, Secciones, Títulos, Capítulos)
  se replica con **carpetas**, y cada nivel tiene una **nota índice**.
- **Referencias convertidas en wikilinks**, también entre normas distintas:
  «artículo 913 del Código de Comercio» → `[[art. 913 CCo|913]]`.
- **Vigencia**: las notas de vigencia, derogatorias e inexequibilidad aparecen
  como *callouts*; los apartes derogados van ~~tachados~~ y cada artículo
  declara su estado (`vigente`, `modificado`, `parcialmente derogado`,
  `derogado`…) en el frontmatter.
- **Navegación**: migas de pan, artículo anterior/siguiente y frontmatter con
  la ubicación jerárquica, listo para Dataview.

Las fuentes son el Gestor Normativo del **Departamento Administrativo de la
Función Pública (DAFP)**
(`https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=<id>`) y la
base documental de la **Secretaría General del Senado**
(`http://www.secretariasenado.gov.co/senado/basedoc/…`). Cada norma se consolida a
partir de ambas, artículo por artículo, con la versión más actualizada.

## Normas disponibles

| Sigla | Norma | Artículos | Fuentes | Estado |
| --- | --- | ---: | --- | --- |
| `CC` | Código Civil (Ley 84 de 1873) | 2.679 | Senado | vigente |
| `CCo` | Código de Comercio (Decreto 410 de 1971) | 2.038 | DAFP + Senado | vigente |
| `CGD` | Código General Disciplinario (Ley 1952 de 2019) | 281 | DAFP + Senado | vigente |
| `CGP` | Código General del Proceso (Ley 1564 de 2012) | 634 | DAFP + Senado | vigente |
| `CP` | Código Penal (Ley 599 de 2000) | 596 | DAFP + Senado | vigente |
| `CPACA` | Código de Procedimiento Administrativo y de lo Contencioso Administrativo (Ley 1437 de 2011) | 321 | DAFP + Senado | vigente |
| `CPP` | Código de Procedimiento Penal (Ley 906 de 2004) | 590 | DAFP + Senado | vigente |
| `CPT` | Código Procesal del Trabajo (derogado por la Ley 2452 de 2025) (Decreto 2158 de 1948) | 149 | DAFP | derogado por la Ley 2452 de 2025 |
| `CPTSS` | Código Procesal del Trabajo y de la Seguridad Social (Ley 2452 de 2025) | 331 | DAFP + Senado | vigente |
| `CPol` | Constitución Política de Colombia (Constitución Política de 1991) | 497 | DAFP + Senado | vigente |
| `CST` | Código Sustantivo del Trabajo (Decreto 2663 de 1950) | 499 | DAFP + Senado | vigente |
| `EOSF` | Estatuto Orgánico del Sistema Financiero (Decreto 663 de 1993) | 343 | DAFP + Senado | vigente |
| `ET` | Estatuto Tributario (Decreto Ley 624 de 1989) | 1.319 | DAFP + Senado | vigente |
| — | Decreto 1082 de 2015 — Decreto Único Reglamentario del Sector Administrativo de Planeación Nacional | 864 | DAFP | vigente |
| — | Decreto 2555 de 2010 — Decreto Único del sector financiero, asegurador y del mercado de valores | 2.565 | DAFP | vigente |
| — | Decreto 92 de 2017 — Contratación con entidades privadas sin ánimo de lucro | 11 | Senado | vigente |
| — | Ley 1150 de 2007 — Medidas para la eficiencia y la transparencia en la Ley 80 de 1993 | 33 | Senado | vigente |
| — | Ley 1258 de 2008 — Sociedad por acciones simplificada (SAS) | 46 | DAFP + Senado | vigente |
| — | Ley 1474 de 2011 — Estatuto Anticorrupción | 142 | DAFP + Senado | vigente |
| — | Ley 1480 de 2011 — Estatuto del Consumidor | 84 | DAFP + Senado | vigente |
| — | Ley 1563 de 2012 — Estatuto de Arbitraje Nacional e Internacional | 119 | DAFP + Senado | vigente |
| — | Ley 1996 de 2019 — Régimen para el ejercicio de la capacidad legal de las personas con discapacidad | 63 | DAFP + Senado | vigente |
| — | Ley 222 de 1995 — Reforma del Libro II del Código de Comercio (sociedades) | 242 | DAFP + Senado | vigente |
| — | Ley 25 de 1992 — Desarrollo de los incisos 9 a 13 del artículo 42 de la Constitución (divorcio y matrimonio religioso) | 15 | Senado | vigente |
| — | Ley 389 de 1997 — Normas en materia de seguros y capitalización | 8 | Senado | vigente |
| — | Ley 446 de 1998 — Descongestión, eficiencia y acceso a la justicia | 167 | DAFP + Senado | vigente |
| — | Ley 472 de 1998 — Acciones populares y de grupo | 87 | DAFP + Senado | vigente |
| — | Ley 489 de 1998 — Organización y funcionamiento de las entidades del orden nacional | 121 | DAFP + Senado | vigente |
| — | Ley 610 de 2000 — Trámite de los procesos de responsabilidad fiscal | 67 | Senado | vigente |
| — | Ley 675 de 2001 — Régimen de propiedad horizontal | 87 | Senado | vigente |
| — | Ley 80 de 1993 — Estatuto General de Contratación de la Administración Pública | 84 | DAFP + Senado | vigente |
| — | Ley 820 de 2003 — Régimen de arrendamiento de vivienda urbana | 43 | DAFP + Senado | vigente |

32 normas y 15.125 artículos, extraídos el 8 de noviembre de 2026. **Cada norma se
consolida a partir de todas sus fuentes** (ver [Consolidación multifuente](#consolidación-multifuente)):
el Gestor Normativo del DAFP y la Secretaría General del Senado. La Constitución también
tiene el alias `CN`; las leyes y decretos sin sigla se citan por su identificador:
`[[art. 3 Ley 80 de 1993]]`, `[[art. 2.2.1.1.1.1.1 Decreto 1082 de 2015]]`.

## Tres formas de usarlo

1. **Plugin de Obsidian** (recomendado): instala «Normas Colombianas» y usa el
   comando *Descargar norma de la biblioteca*. Mientras se aprueba en la tienda de
   Obsidian, se instala a mano desde el
   [último release](https://github.com/adolfo-s-rey-b/normas-obsidian/releases/latest)
   o con [BRAT](https://obsidian.md/plugins?id=obsidian42-brat). Ver
   [`plugin-obsidian/README.md`](plugin-obsidian/README.md).
2. **Copiar a mano**: copia la carpeta de la norma desde [`biblioteca/`](biblioteca/)
   a tu *vault*.
3. **Generarla tú mismo** con el CLI (cualquier norma del DAFP, directo a tu
   *vault*). Ver más abajo.

### Plugin: uso de red y datos

El plugin se conecta **solo** a `raw.githubusercontent.com` (o a la URL base del
catálogo que configures) para leer `catalogo/index.json` y el paquete de la norma
elegida, y **únicamente** cuando ejecutas uno de sus comandos. No envía datos de
tu vault ni tuyos, no tiene telemetría y no se conecta en segundo plano. Escribe
solo dentro de la carpeta destino (por defecto `Normas/`) y pide confirmación
antes de reemplazar una norma ya descargada.

## Estructura del repositorio

```text
normas-obsidian/
├── extractor/        CLI en Python (descarga, parseo, conversión, verificación)
│   ├── normas_cli/
│   ├── registry.yaml  normas de la biblioteca y diccionario de siglas
│   └── tests/
├── biblioteca/       normas convertidas, listas para copiar a un vault
├── catalogo/         index.json + un paquete JSON por norma (lo usa el plugin)
├── plugin-obsidian/  código del plugin (TypeScript)
├── e2e/              pruebas de punta a punta en Obsidian real (CLI de Obsidian)
├── manifest.json     manifest del plugin (en la raíz, como exige Obsidian)
└── versions.json
```

## Notas generadas

```text
biblioteca/CGP/
├── CGP.md                                   nota raíz: datos, tabla de contenido, preámbulo, firmas
├── 1. TÍTULO PRELIMINAR - DISPOSICIONES GENERALES/
│   ├── CGP - Título Preliminar.md           nota índice del nivel
│   └── art. 1 CGP.md …
└── 2. LIBRO PRIMERO - SUJETOS DEL PROCESO/
    └── 1. SECCIÓN PRIMERA - …/1. TÍTULO I - …/1. CAPÍTULO I - Competencia/
        └── art. 22 CGP.md
```

### Nombres y alias

- Artículo: `art. N <ETIQUETA>.md`, donde la etiqueta es la **sigla** (`CGP`) o,
  si la norma no tiene, el identificador (`Ley 1996 de 2019`).
- Números compuestos y con letra se conservan: `art. 115-1 ET`, `art. 397A CGP`.
- **Transitorios**: `art. transitorio 1 CPol`. Cuando un Acto Legislativo reinicia
  la numeración se añade el acto: `art. transitorio 1 (AL 1 de 2017) CPol`; los
  transitorios sin número toman el acto que los adicionó:
  `art. transitorio (AL 1 de 2016) 2 CPol`.
- **Para enlazar, usa el nombre de la nota**: `[[art. 22 CGP]]`. Obsidian
  resuelve los wikilinks solo por nombre de archivo; **un `[[alias]]` escrito a
  mano queda sin resolver**.
- Cada artículo tiene además alias con otras notaciones (`art. 22 Ley 1564 de
  2012`, `CGP art. 22`, `CGP 22`, `art. 410-A CP` para los artículos con letra,
  `art. 29 CN` para la Constitución). Sirven para el buscador rápido
  (<kbd>Ctrl</kbd>+<kbd>O</kbd>) y el autocompletado: al escribir `[[art. 22 Ley 1564`
  y elegir la sugerencia, Obsidian inserta `[[art. 22 CGP|art. 22 Ley 1564 de 2012]]`,
  que sí resuelve. `normas-cli verificar` marca como error cualquier enlace que
  dependa solo de un alias.
- Nota raíz: `CGP.md` (alias `Ley 1564 de 2012` y `Código General del Proceso` para el buscador).
- Nota índice: `CGP - Libro Primero - Sección Primera - Título I - Capítulo I.md`.

### Frontmatter de un artículo

```yaml
aliases: ["CGP art. 22", "art. 22 Ley 1564 de 2012", "Ley 1564 de 2012 art. 22", "CGP 22"]
tipo: articulo                 # articulo | indice | norma
norma: "Ley 1564 de 2012"
sigla: "CGP"
articulo: "22"
epigrafe: "Competencia de los jueces de familia en primera instancia"
libro: "[[CGP - Libro Primero|LIBRO PRIMERO - SUJETOS DEL PROCESO]]"
seccion: "[[…|SECCIÓN PRIMERA - …]]"
titulo: "[[…|TÍTULO I - JURISDICCIÓN Y COMPETENCIA]]"
capitulo: "[[…|CAPÍTULO I - Competencia]]"
vigencia: "parcialmente derogado"   # vigente | modificado | parcialmente derogado |
                                    # parcialmente inexequible | derogado | inexequible
modificado_por: ["[[art. 35 Ley 1996 de 2019]]"]
derogado_por: ["[[art. 61 Ley 1996 de 2019]]"]
anterior: "[[art. 21 CGP]]"
siguiente: "[[art. 23 CGP]]"
fuente: "http://www.secretariasenado.gov.co/senado/basedoc/ley_1564_2012.html"
fuente_texto: "Senado"               # fuente de la que se tomó este texto
fuentes_comparadas: "DAFP, Senado"
coincidencia_fuentes: "difiere"      # idéntico | difiere | solo en <fuente>
reforma_mas_reciente: 2019           # evento de vigencia más reciente citado
actualizacion_fuente: "27 de agosto de 2025"
fecha_extraccion: 2026-11-07
tags: [normas/articulo, normas/cgp, vigencia/parcialmente_derogado]
```

Ejemplo con [Dataview](https://blacksmithgu.github.io/obsidian-dataview/):

```dataview
TABLE epigrafe, vigencia FROM #normas/cgp
WHERE tipo = "articulo" AND vigencia != "vigente"
```

### Enlaces entre normas

- Sin marcador, «de este código», «de la presente ley» → misma norma.
- «del Código de Comercio», «de la Constitución Política» → sigla del
  diccionario `codigos` de `registry.yaml` (gana el nombre más largo).
- «de la Ley 1996 de 2019», «del Decreto Nacional 1736 de 2012» → sigla si la
  norma está registrada; si no, `Ley 1996 de 2019` / `Decreto 1736 de 2012`.
  Al agregar esa norma y regenerar la biblioteca, el enlace se recalcula con la
  etiqueta definitiva (la sigla, si se le asigna una).
- No se enlazan los números de numerales, incisos, literales, parágrafos,
  sentencias ni años, ni las referencias a un «Código X» desconocido o a «el
  citado código». Ante la duda, el motor prefiere **no** enlazar.
- El texto citado de otra norma («Modifíquese el artículo 577 de la Ley 1564 de
  2012, así: "…"») se enlaza a la norma citada.

## Uso del CLI

Requisitos: Python 3.10+.

```bash
cd extractor
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"           # instala el comando normas-cli
```

```bash
# Una norma por id del DAFP (norma.php?i=48425), con sigla:
normas-cli 48425 --sigla CGP --output /ruta/a/tu/Vault

# Por URL completa:
normas-cli "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=99712"

# Desde HTML guardado con el navegador (indica el id para conservar la fuente):
normas-cli ./pagina.html --id 48425 --sigla CGP

# Regenerar todas las normas del registry (con caché del HTML descargado):
normas-cli todas
normas-cli todas --solo CGP ET

# Revisar la biblioteca (duplicados, alias ambiguos, carpetas vacías, enlaces):
normas-cli verificar
normas-cli verificar --estricto          # también falla por enlaces internos rotos

# Generar el catálogo para el plugin:
normas-cli catalogo

# Comparar una norma entre el DAFP y el Senado (informe Markdown):
normas-cli comparar CGP --salida comparacion-cgp.md
```

## Consolidación multifuente

Las fuentes oficiales se actualizan en fechas distintas y con criterios propios, y
**ninguna es siempre la más reciente**: difieren artículo por artículo (p. ej., para el
CGP el Senado ya incorpora la Ley 2445 de 2025, que el DAFP aún no tenía; en otros
artículos ocurre al revés). Por eso `normas-cli` construye cada norma así:

1. Descarga **todas** las fuentes disponibles: el DAFP (`id` en el registry) y el
   Senado (`url_senado`, o la URL estándar `ley_NNNN_AAAA.html`).
2. Toma como estructura (jerarquía, preámbulo, firmas) la del Senado si cubre al
   menos el 95 % de los artículos; si no, la más completa.
3. **Por cada artículo elige la versión con el evento de vigencia más reciente**
   citado en sus notas: reformas («modificado por el art. 3 de la Ley 2445 de 2025»)
   y sentencias de la Corte Constitucional (una inexequibilidad posterior revive el
   texto anterior, p. ej. el art. 4 de la Ley 1258 de 2008 tras la C-038-25). En
   empate, la fuente base. Los artículos que solo trae una fuente se incorporan.
4. Cada nota indica `fuente_texto`, `fuentes_comparadas`, `coincidencia_fuentes`
   y `reforma_mas_reciente`; la nota raíz resume la comparación y lista los
   artículos con diferencias.

`normas-cli comparar <norma>` produce el informe detallado de diferencias entre
fuentes (texto normativo por artículo y reformas citadas solo por cada una).

## El registry (`extractor/registry.yaml`)

Lista las normas de la biblioteca (`id`, identidad, `sigla`, `nombre`, `ruta`,
`estado`) y el diccionario `codigos` (nombre de código → sigla). Admite dos
ajustes por norma para páginas difíciles:

- `url_senado`: página de la norma en el Senado, si no sigue el patrón `ley_NNNN_AAAA.html` (o `false` para no usarla).
- `jerarquia`: orden forzado de niveles, p. ej. `[LIBRO, PARTE, TÍTULO, CAPÍTULO, SECCIÓN]` (CCo).
- `esquema`: niveles a insertar antes de ciertos artículos, para páginas sin
  encabezados fiables. La Constitución lo usa porque el DAFP omite las
  etiquetas «TÍTULO I», «CAPÍTULO 1».

## Cómo funciona el parser

El HTML del DAFP tiene varias generaciones de marcado. El parser:

- Usa `html5lib`, que repara el HTML mal anidado como lo haría un navegador
  (páginas antiguas con `<P>` sin cerrar).
- Acepta una cabecera «ARTÍCULO N» solo si **continúa la secuencia** de
  numeración; así las enumeraciones de un artículo de derogatorias o los
  artículos citados de otra norma no crean notas falsas.
- Toma el epígrafe de la **negrita inicial** de la cabecera; si la norma pone la
  rúbrica fuera de la negrita (Ley 1996), lo detecta solo cuando es el patrón
  dominante.
- **Infiere el orden de los niveles** en cada norma (en el CGP la SECCIÓN va
  sobre el TÍTULO; en el CCo, bajo el CAPÍTULO).
- Reconoce tablas, listas `<ol>`, notas editoriales, firmas y la norma
  «envoltura» (los artículos del Decreto 624 de 1989 que expide el ET van en la
  nota raíz y no chocan con los del Estatuto).

### Descarga y certificado TLS del DAFP

El servidor del DAFP envía una cadena de certificados incompleta, por lo que
`requests` falla con `CERTIFICATE_VERIFY_FAILED`. El CLI la completa igual que un
navegador: descarga el certificado intermedio indicado por el propio
certificado (AIA) y verifica la cadena completa contra las raíces de `certifi`.
La verificación TLS **nunca** se desactiva.

## Desarrollo y pruebas

```bash
cd extractor && pytest -q                 # 58 pruebas sobre HTML real del DAFP y del Senado
cd plugin-obsidian && npm ci && npm run lint && npm run build && npm test
```

`npm run lint` aplica `eslint-plugin-obsidianmd`, las mismas reglas que usa la
revisión automática de la tienda de Obsidian. La CI de GitHub Actions ejecuta todo
lo anterior y `normas-cli verificar` sobre la biblioteca. Los fixtures se describen en
[`extractor/tests/README.md`](extractor/tests/README.md).

### Pruebas de punta a punta en Obsidian real

`e2e/` prueba el plugin en una instalación real de Obsidian (1.15) a través de
su CLI, con capturas de pantalla e informe. Usa un vault y una configuración
**aislados**: nunca abre ni modifica tu vault ni tu configuración. Con
`VAULT_ORIGEN` copia (solo lectura) una carpeta de tus notas para medir cuántos
de tus enlaces `[[art. N X]]` resuelven.

```bash
export E2E_DIR=/tmp/normas-e2e
VAULT_ORIGEN=~/ruta/a/tu/vault e2e/preparar.sh   # vault de pruebas (+ copia de Derecho/)
e2e/servir.sh &                                  # catálogo local en http://127.0.0.1:8765
e2e/obsidian.sh &                                # Obsidian aislado (cierra tu Obsidian antes)
node e2e/run.mjs                                 # 14 escenarios → $E2E_DIR/informe.md
```

Para probar **contra GitHub** (el catálogo publicado y los ajustes por defecto), tras
`preparar.sh` escribe `{"destino":"Normas"}` en
`$E2E_DIR/vault/.obsidian/plugins/normas-colombianas/data.json` (sin `urlBase`) y,
si quieres probar exactamente lo publicado, copia ahí el `main.js` del release.
`servir.sh` solo hace falta entonces para el escenario `errores`.

Escenarios: arranque sin errores, descarga por la paleta, descarga de todas las
normas, resolución de enlaces de tus notas, visualización (tachados, callouts,
tablas, índices), vista previa, navegación, propiedades y Dataview, búsqueda,
actualización con confirmación, errores de red y de versión, ajustes y vista
móvil. Resultados medidos (Obsidian 1.15, Linux, contra GitHub, 8 de noviembre de
2026): las 32 normas (17.979 notas, 50 MB) se instalan en unos 7 minutos (el
Decreto 2555 de 2010, el más grande, en ~100 s); de 1.315 enlaces a artículos en
un vault real de apuntes de Derecho, 1.234 resuelven (los 81 restantes apuntan a
normas ausentes o tienen errores de escritura). Tras instalar miles de notas,
Obsidian y Dataview tardan unos minutos en indexarlas.

## Publicación

1. **Versión**: `cd plugin-obsidian && npm version X.Y.Z --no-git-tag-version`
   (actualiza `package.json`, `manifest.json` y `versions.json`), commit y push a
   `main`, esperar la CI en verde.
2. **Release**: `git tag -a X.Y.Z -m "Normas Colombianas X.Y.Z" && git push origin X.Y.Z`
   (sin «v»); el workflow `release.yml` compila y adjunta `main.js` y `manifest.json`.
3. **Tienda de Obsidian**: desde mayo de 2026 los plugins se envían en
   [community.obsidian.md](https://community.obsidian.md) (cuenta de Obsidian con
   GitHub vinculado → panel de desarrollador → elegir este repositorio), ya no por
   PR a `obsidianmd/obsidian-releases`. El portal lee `manifest.json` de `main`,
   instala desde el release con el mismo tag y pasa una revisión automática
   (`eslint-plugin-obsidianmd`, malware, políticas) en cada versión; si una versión
   falla, el plugin sale de la búsqueda en 24 h. El panel permite un *preview scan*
   de cualquier rama, tag o commit antes de publicar.

## Pendientes

- **Tienda de Obsidian**: enviar el plugin en community.obsidian.md (versión 0.4.1
  publicada y lista; lo hace el titular de la cuenta) y atender la revisión automática.
- **Ajustes en la búsqueda de Obsidian 1.13+**: implementar `getSettingDefinitions()`
  (API declarativa) sin romper la compatibilidad con 1.6.6; hoy es solo un aviso del escáner.
- **Más fuentes**: SUIN-Juriscol sería una tercera fuente para la consolidación.
  Algunas normas solo están en una fuente (Código Civil y varias leyes, solo en el
  Senado; CPT y decretos únicos, solo en el DAFP).
- **Normas citadas aún fuera de la biblioteca**: Ley 5 de 1992, Ley 1819 de 2016,
  Ley 1676 de 2013, Ley 527 de 1999… (`normas-cli verificar` lista las más enlazadas).
- **Constitución**: los capítulos 5 a 7 de las disposiciones transitorias de
  1991 no tienen encabezado en la fuente; esos transitorios quedan directamente
  bajo «Disposiciones transitorias».
- Las tablas con celdas combinadas (algunas del ET) se convierten de forma
  aproximada.
- Algunos enlaces se omiten a propósito cuando la referencia es ambigua (p. ej.
  «el 766 inciso final, y 1434 del Código Civil» enlaza el 766 pero no el 1434).

## Licencia

Código bajo licencia MIT (ver [`LICENSE`](LICENSE)). Los textos normativos son
de dominio público; las anotaciones editoriales (notas de vigencia,
jurisprudencia) pertenecen a sus editores.
