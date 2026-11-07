# Plugin de Obsidian — Normas Colombianas

Plugin **fino**: no descarga de los sitios del gobierno (eso lo hace el CLI de
Python). En su lugar, lista las normas ya convertidas en la carpeta
`biblioteca/` de este repositorio y descarga la que elijas directamente a tu
*vault*, conservando la estructura de carpetas y los wikilinks.

## Uso

1. Comando: **«Descargar norma de la biblioteca»** (paleta de comandos).
2. Elige la norma en el selector.
3. Las notas se crean bajo la carpeta destino configurada (por defecto `Normas/`).

## Ajustes

- **Repositorio**: `usuario/repositorio` con la biblioteca (por defecto
  `argonautarey/normas-obsidian`).
- **Rama**: por defecto `main`.
- **Carpeta de biblioteca**: ruta dentro del repo (por defecto `biblioteca`).
- **Carpeta destino**: dónde guardar las normas en tu *vault* (por defecto `Normas`).

## Compilar

```bash
cd plugin-obsidian
npm install
npm run build      # genera main.js
```

Luego copia `manifest.json` y `main.js` a
`<TuVault>/.obsidian/plugins/normas-colombianas/` y activa el plugin.

> El plugin usa `requestUrl` de la API de Obsidian para evitar restricciones de
> CORS al consultar la API de GitHub y `raw.githubusercontent.com`.
