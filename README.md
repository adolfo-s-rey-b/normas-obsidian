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

La fuente es el Gestor Normativo del **Departamento Administrativo de la
Función Pública (DAFP)**:
`https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=<id>`.

## Normas disponibles

| Sigla | Norma | Artículos | Fuente | Estado |
| --- | --- | ---: | --- | --- |
| `CPol` | Constitución Política de 1991 (alias `CN`) | 484 | DAFP | vigente |
| `CC` | Código Civil (Ley 84 de 1873) | 2.679 | Senado | vigente |
| `CCo` | Código de Comercio (Decreto 410 de 1971) | 2.037 | DAFP | vigente |
| `CGP` | Código General del Proceso (Ley 1564 de 2012) | 628 | DAFP | vigente |
| `CPACA` | Código de Procedimiento Administrativo y de lo Contencioso Administrativo (Ley 1437 de 2011) | 320 | DAFP | vigente |
| `CP` | Código Penal (Ley 599 de 2000) | 588 | DAFP | vigente |
| `CPP` | Código de Procedimiento Penal (Ley 906 de 2004) | 590 | DAFP | vigente |
| `CST` | Código Sustantivo del Trabajo (Decreto 2663 de 1950) | 496 | DAFP | vigente |
| `CPTSS` | Código Procesal del Trabajo y de la Seguridad Social (Ley 2452 de 2025) | 331 | DAFP | vigente |
| `CPT` | Código Procesal del Trabajo (Decreto 2158 de 1948) | 149 | DAFP | derogado por la Ley 2452 de 2025 |
| `ET` | Estatuto Tributario (Decreto Ley 624 de 1989) | 1.307 | DAFP | vigente |
| — | Ley 80 de 1993 (contratación estatal) | 83 | DAFP | vigente |
| — | Ley 222 de 1995 (reforma del régimen de sociedades) | 242 | DAFP | vigente |
| — | Ley 446 de 1998 (descongestión y acceso a la justicia) | 167 | DAFP | vigente |
| — | Ley 472 de 1998 (acciones populares y de grupo) | 87 | DAFP | vigente |
| — | Ley 820 de 2003 (arrendamiento de vivienda urbana) | 43 | DAFP | vigente |
| — | Ley 1258 de 2008 (SAS) | 46 | DAFP | vigente |
| — | Ley 1474 de 2011 (Estatuto Anticorrupción) | 142 | DAFP | vigente |
| — | Ley 1996 de 2019 (capacidad legal de las personas con discapacidad) | 63 | DAFP | vigente |

19 normas y 10.482 artículos, extraídos el 7 de noviembre de 2026; cada nota
indica su fuente y fecha. El **Código Civil** no está en el Gestor Normativo del
DAFP, así que se toma de la [Secretaría General del Senado](http://www.secretariasenado.gov.co/senado/basedoc/codigo_civil.html)
(compilación de Avance Jurídico; sus epígrafes son editoriales). Las leyes sin
sigla se citan por su identificador: `[[art. 3 Ley 80 de 1993]]`.

## Tres formas de usarlo

1. **Plugin de Obsidian** (recomendado): instala «Normas Colombianas» y usa el
   comando *Descargar norma de la biblioteca*. Ver
   [`plugin-obsidian/README.md`](plugin-obsidian/README.md).
2. **Copiar a mano**: copia la carpeta de la norma desde [`biblioteca/`](biblioteca/)
   a tu *vault*.
3. **Generarla tú mismo** con el CLI (cualquier norma del DAFP, directo a tu
   *vault*). Ver más abajo.

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
fuente: "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=48425#22"
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

### Dos fuentes: DAFP y Senado

La fuente principal es el DAFP; el Senado (compilación de Avance Jurídico) se
usa para normas que el DAFP no publica (`fuente: senado` en el registry, hoy el
Código Civil). `normas-cli comparar` descarga la norma de ambas, alinea los
artículos por número y compara el **texto normativo** (sin notas, tachados ni
puntuación): fechas de actualización declaradas, artículos idénticos, con
diferencias y presentes en una sola fuente, con extractos. Ninguna fuente es
siempre la más reciente: las diferencias aparecen artículo por artículo, por eso
el informe sirve para decidir y corregir, no se fusiona automáticamente.

| Opción | Descripción |
| --- | --- |
| `--sigla` | Sigla corta para nombrar las notas (`CGP`, `CCo`…). Si se omite, se usa la del registry o el identificador `Ley N de A`. |
| `--id` | Id del DAFP cuando el origen es un archivo local. |
| `--output, -o` | Carpeta de salida (por defecto `biblioteca/`). Apunta a tu *vault* para uso local. |
| `--registry, -r` | Ruta del `registry.yaml`. |
| `--cache-dir` | Guarda y reutiliza el HTML descargado (`todas` usa `~/.cache/normas-obsidian/html`). |
| `--forzar` | Reemplaza la carpeta de salida aunque no parezca generada por `normas-cli`. |
| `--no-update-registry` | No registrar la norma en `registry.yaml`. |

La carpeta de cada norma se **reemplaza completa** en cada generación (se
escribe en un directorio temporal y luego se intercambia), así no quedan notas
obsoletas. Por seguridad, el CLI se niega a reemplazar una carpeta que no
parezca generada por él.

### `registry.yaml`

Lista las normas de la biblioteca (`id`, identidad, `sigla`, `nombre`, `ruta`,
`estado`) y el diccionario `codigos` (nombre de código → sigla). Admite dos
ajustes por norma para páginas difíciles:

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
cd extractor && pytest -q                 # 48 pruebas sobre HTML real del DAFP
cd plugin-obsidian && npm ci && npm run build && npm test
```

La CI de GitHub Actions ejecuta ambas y `normas-cli verificar` sobre la
biblioteca. Los fixtures se describen en
[`extractor/tests/README.md`](extractor/tests/README.md).

Para publicar una versión del plugin: `cd plugin-obsidian && npm version 0.2.1`
(actualiza `manifest.json` y `versions.json`), y luego empujar el tag `0.2.1`;
el workflow `release.yml` compila y crea el release con `main.js` y
`manifest.json`.

## Pendientes

- **Código Civil**: no está en el Gestor Normativo del DAFP. Hace falta un
  adaptador para otra fuente oficial (Secretaría del Senado o SUIN-Juriscol).
- **Leyes muy citadas** aún fuera de la biblioteca: Ley 5 de 1992, Ley 1819 de
  2016, Ley 2010 de 2019, Ley 80 de 1993, Ley 50 de 1990… (`normas-cli
  verificar` lista las más enlazadas). Basta con agregarlas: los enlaces ya
  existentes resolverán solos.
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
