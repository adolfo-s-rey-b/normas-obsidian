# Normas Colombianas — plugin de Obsidian

Descarga a tu *vault* normativa colombiana ya convertida a notas de Obsidian:
un artículo por nota, carpetas por Libro/Título/Capítulo, notas índice,
estado de vigencia y enlaces entre artículos y normas.

El plugin **no** hace *scraping* de sitios del gobierno: descarga normas ya
convertidas y verificadas desde el catálogo del repositorio
[`adolfo-s-rey-b/normas-obsidian`](https://github.com/adolfo-s-rey-b/normas-obsidian).

## Uso

- **Descargar norma de la biblioteca** (paleta de comandos): elige la norma en
  el selector (muestra sigla, nombre, número de artículos, tamaño y si ya la
  tienes o hay actualización). La norma se guarda en `Normas/<sigla>/`.
- **Actualizar normas descargadas**: compara tus normas con el catálogo y
  reemplaza las que tengan una versión nueva.

Al reemplazar una norma, las notas de su carpeta que ya no existan en la
biblioteca se envían a la papelera (según tu configuración de Obsidian). El
plugin pide confirmación antes, porque **los cambios que hayas hecho dentro de
esas notas se pierden**. Escribe tus propias notas fuera de la carpeta de la
norma y enlázalas con `[[art. 22 CGP]]`.

## Ajustes

| Ajuste | Por defecto | |
| --- | --- | --- |
| Carpeta destino | `Normas` | Carpeta del vault para las normas. |
| Repositorio | `adolfo-s-rey-b/normas-obsidian` | Repositorio de GitHub que publica el catálogo. |
| Rama | `main` | |
| Carpeta del catálogo | `catalogo` | |
| URL base del catálogo | *(vacío)* | Avanzado: usar un espejo o servidor propio en lugar de GitHub. |

Cada norma recuerda la carpeta donde se instaló: si cambias la carpeta destino,
«Actualizar» sigue actualizándola en su sitio.

Las normas grandes traen miles de notas (el Código Civil, casi 3.000). Tras la
descarga, Obsidian y plugins como Dataview pueden tardar unos minutos en
indexarlas; mientras tanto, búsquedas y consultas pueden salir incompletas.

## Uso de red

Para cumplir las [directrices de Obsidian](https://docs.obsidian.md/Developer+policies):
el plugin se conecta **solo** a `raw.githubusercontent.com`, para leer
`catalogo/index.json` y el paquete JSON de la norma que elijas, y **únicamente**
cuando ejecutas uno de sus comandos. No envía datos del vault ni del usuario,
no tiene telemetría y no se conecta en segundo plano.

## Instalación manual

1. Descarga `main.js` y `manifest.json` del
   [último release](https://github.com/adolfo-s-rey-b/normas-obsidian/releases).
2. Cópialos a `<TuVault>/.obsidian/plugins/normas-colombianas/`.
3. Activa «Normas Colombianas» en *Ajustes → Plugins de la comunidad*.

## Desarrollo

```bash
cd plugin-obsidian
npm ci
npm run build      # genera main.js (comprueba tipos con tsc)
npm test           # prueba de humo con un vault simulado y el catálogo local
npm run lint       # reglas de eslint-plugin-obsidianmd (las del escáner de la tienda)
npm run dev        # compila en modo watch
```

`manifest.json` y `versions.json` están en la raíz del repositorio (la tienda de
Obsidian los busca ahí). `npm version X.Y.Z` los actualiza; al empujar el tag
`X.Y.Z`, el workflow `release.yml` publica el release.

### Publicación en la tienda

Los plugins se envían en [community.obsidian.md](https://community.obsidian.md)
(cuenta de Obsidian con GitHub vinculado → panel de desarrollador → elegir este
repositorio); ya no se hace por PR a `obsidianmd/obsidian-releases`. El portal lee
`manifest.json` de la rama `main` y descarga los archivos del release cuyo tag
coincide con la versión. Cada versión pasa por una revisión automática basada en
`eslint-plugin-obsidianmd`: `npm run lint` (también en la CI) aplica las mismas
reglas antes de publicar.
