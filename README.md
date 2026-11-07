# Normas Colombianas → Obsidian

Convierte normativa colombiana (leyes, decretos, resoluciones, códigos) en una
estructura de [Obsidian](https://obsidian.md) donde:

- La **jerarquía** de la norma (Libros, Títulos, Capítulos, Secciones) se
  replica con **carpetas**.
- Cada **artículo** es una **nota** de Markdown (`art. N <SIGLA>.md`).
- Los **numerales, literales y parágrafos** se conservan con notación Markdown.
- Las **referencias entre artículos** se convierten en **wikilinks de Obsidian**
  (`[[art. 28 CGP]]`), incluso entre normas distintas (referencias cruzadas).
- Las **notas de vigencia, derogatorias y de constitucionalidad** se incluyen
  como *callouts*; los apartes derogados se muestran ~~tachados~~.

La fuente es el gestor normativo del **Departamento Administrativo de la Función
Pública (DAFP)**: `https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=<id>`.

## Componentes

```
normas-obsidian/
├── extractor/        # CLI en Python (el motor de scraping + conversión)
├── biblioteca/       # Normas ya convertidas, listas para usar en Obsidian
└── plugin-obsidian/  # (opcional) plugin que descarga normas de la biblioteca al vault
```

- **`extractor/`** — Convierte cualquier norma a la estructura de Obsidian.
  Úsalo 100% local (genera directo en tu *vault*) o para alimentar la biblioteca
  central de este repositorio.
- **`biblioteca/`** — Catálogo de normas ya convertidas y versionadas. Cualquiera
  puede copiarlas a su *vault* sin instalar nada.
- **`plugin-obsidian/`** — Plugin fino que lista la biblioteca del repositorio y
  descarga la norma elegida directamente al *vault* (no hace scraping; evita
  restricciones de CORS).

## Uso del CLI

Requisitos: Python 3.10+.

```bash
cd extractor
pip install -e .            # instala el comando `normas-cli` y sus dependencias

# Por id de Función Pública (norma.php?i=48425), asignando una sigla:
normas-cli 48425 --sigla CGP --output /ruta/a/tu/Vault

# Por URL completa:
normas-cli "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=99712"

# Desde un archivo HTML local (p. ej. una muestra guardada):
normas-cli ./pagina.html --sigla CST
```

Opciones:

| Opción | Descripción |
|---|---|
| `--sigla` | Sigla corta para nombrar las notas (`CGP`, `CCo`, `CST`…). Si se omite, se usa el identificador `Ley N de A`. |
| `--output, -o` | Carpeta de salida (por defecto `../biblioteca`). Apunta a tu *vault* para uso local. |
| `--registry, -r` | Ruta del `registry.yaml` (mapa id↔sigla y diccionario de códigos). |
| `--no-update-registry` | No registrar la norma en `registry.yaml`. |

### Notación de notas y wikilinks (consistencia entre normas)

- El nombre de archivo es `art. N <ETIQUETA>.md`, donde `<ETIQUETA>` es la
  **sigla** si la indicas, o el identificador `Ley N de A` si no.
- Cada nota incluye en su *frontmatter* **alias** con **ambas** notaciones, de
  modo que tanto `[[art. 28 CGP]]` como `[[art. 28 Ley 1564 de 2012]]` resuelven
  a la **misma** nota. Así, al ir agregando normas, las referencias previas no se
  rompen aunque cambie la sigla.
- Las referencias a **otras** normas se enlazan usando el marcador del texto
  (`del Código de Comercio` → `CCo`, `de la Ley 1996 de 2019` → identificador).
  El `registry.yaml` define el diccionario de siglas de códigos.

## Cómo funciona el parser

El HTML del DAFP tiene varias generaciones de marcado. El parser es **tolerante
a variantes** porque clasifica los párrafos por su **contenido de texto** (no por
la anidación exacta de etiquetas) y normaliza entidades, tildes y mayúsculas.
Verificado sobre tres generaciones:

- **Códigos modernos** (p. ej. CGP, `i=48425`): `<strong>Artículo N. <em>…</em>`.
- **Leyes recientes** (p. ej. Ley 1996 de 2019, `i=99712`): entidades HTML,
  mayúsculas, epígrafe fuera de `<em>`.
- **Decretos antiguos** (p. ej. Decreto 2651 de 1991, `i=14319`): `<P>` en
  mayúsculas, atributos sin comillas y HTML malformado.

> **Limitación conocida:** en páginas muy antiguas con HTML severamente roto
> (etiquetas sin cerrar) algún artículo puede quedar fusionado con el preámbulo.
> Para esos casos, revisa la nota índice `art. INTRO`.

## Desarrollo y pruebas

```bash
cd extractor
pip install -e ".[dev]"
pytest -q     # pruebas sobre fixtures reales de las tres variantes + cruces
```

## Licencia

Código bajo licencia MIT (ver `LICENSE`). Los textos normativos son de dominio
público; las anotaciones editoriales pertenecen a sus editores.
