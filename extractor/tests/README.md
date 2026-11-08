# Pruebas del extractor

`pytest -q` desde `extractor/` (con el entorno de desarrollo instalado).

## Fixtures (`fixtures/`)

| Archivo | Norma | Qué cubre |
| --- | --- | --- |
| `cgp_i48425.html` | CGP (completo) | `<em>` en la rúbrica, jerarquía LIBRO › SECCIÓN › TÍTULO › CAPÍTULO, art. 626 con enumeraciones |
| `ley1996_i99712.html` | Ley 1996 de 2019 (completa) | rúbrica fuera de la negrita, firmas, cruce de derogatoria con el CGP |
| `decreto2651_i14319.html` | Decreto 2651 de 1991 (completo) | `<P>` sin cerrar, varios artículos en un párrafo |
| `cn_i4125_recorte.html` | Constitución (extracto) | sin epígrafes, transitorios en varias series (AL 2017), esquema del registry |
| `et_i6533_recorte.html` | Estatuto Tributario (extracto) | norma «envoltura» (Decreto 624 de 1989), numeración `N-M` |
| `cco_i41102_recorte.html` | Código de Comercio (extracto) | rúbrica en `<strong>` separado, dos artículos en un mismo `<p>` |
| `cst_i199983_recorte.html` | CST (extracto) | numerales en listas `<ol>/<li>` |
| `senado_cc_pr001_recorte.html` + `.js` | Código Civil, Senado (extracto) | adaptador del Senado: recuadros de vigencia en JS, `<S>` tachado, normalización a HTML tipo DAFP |

Los extractos se generan con `recortar_fixture.py` a partir del HTML cacheado en
`~/.cache/normas-obsidian/html/` (lo crea `normas-cli todas`). Son HTML reales
del DAFP (y del Senado), recortados por tramos de párrafos completos.
