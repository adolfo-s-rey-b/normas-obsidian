"""Renderiza una :class:`Norma` a la estructura de carpetas/notas de Obsidian.

  * Jerarquía (LIBRO/TÍTULO/CAPÍTULO…) → carpetas con prefijo incremental.
  * Cada artículo → una nota ``art. N <ETIQUETA>.md`` con frontmatter (alias
    duales sigla/identificador), epígrafe como ``##`` y cuerpo en markdown.
  * Numerales/literales como listas, parágrafos en negrita.
  * Notas editoriales → callouts; incisos derogados → ``~~tachado~~``.
"""

from __future__ import annotations

import re
from pathlib import Path

from .links import enlace_de_href, enlazar
from .model import Articulo, Bloque, Nivel, Norma
from .registry import Registry

_INVALIDOS = re.compile(r'[\\/:*?"<>|]+')


def _slug(texto: str, *, limite: int = 120) -> str:
    texto = _INVALIDOS.sub("-", texto).strip().strip(".")
    texto = re.sub(r"\s+", " ", texto)
    return texto[:limite].strip()


def _nombre_carpeta(idx: int, nivel: Nivel) -> str:
    base = f"{idx}. {nivel.tipo} {nivel.etiqueta}".strip()
    if nivel.nombre:
        base += f" - {nivel.nombre}"
    return _slug(base)


def _aliases(num: str, norma: Norma) -> list[str]:
    canon = norma.nombre_canonico
    etq = norma.etiqueta_nota
    formas = [
        f"art. {num} {etq}",
        f"art. {num} {canon}",
        f"{etq} art. {num}",
        f"{canon} art. {num}",
    ]
    if norma.sigla:
        formas += [f"art. {num} {norma.sigla}", f"{norma.sigla} {num}"]
    # Únicas, preservando orden, sin la idéntica al nombre de archivo.
    archivo = f"art. {num} {etq}"
    vistos, out = set(), []
    for f in formas:
        if f != archivo and f not in vistos:
            vistos.add(f)
            out.append(f)
    return out


def _frontmatter(art: Articulo, norma: Norma) -> str:
    lineas = ["---", "aliases:"]
    for a in _aliases(art.numero, norma):
        lineas.append(f'  - "{a}"')
    lineas.append(f'norma: "{norma.nombre_canonico}"')
    if norma.sigla:
        lineas.append(f"sigla: {norma.sigla}")
    lineas.append(f'articulo: "{art.numero}"')
    if norma.url_fuente:
        lineas.append(f"fuente: {norma.url_fuente}#{art.numero}")
    lineas.append("---")
    return "\n".join(lineas)


def _render_nota(b: Bloque, reg: Registry) -> str:
    texto = b.texto.strip().strip("()").strip()
    # Usa el href como ground truth: convierte la mención "Art. NN" en un
    # wikilink mostrando "Art. NN" y conservando el resto de la frase.
    for h in b.hrefs:
        if not (h.i and h.art):
            continue
        etq = reg.etiqueta_por_id(h.i, h.texto)
        if not etq:
            continue
        wl = f"[[art. {h.art} {etq}|Art. {h.art}]]"
        nuevo, n = re.subn(
            rf"\bart[íi]?(?:culo)?\.?\s*{re.escape(h.art)}\b", wl, texto, count=1, flags=re.I
        )
        texto = nuevo if n else f"{texto} ([[art. {h.art} {etq}]])"
    clase = b.clase_nota or "note"
    cuerpo = texto.replace("\n", " ")
    return f"> [!{clase}] {cuerpo}"


def _render_paragrafo(texto: str) -> str:
    m = re.match(r"(par[áa]grafo[^.]*?\.)\s*(.*)$", texto, re.I | re.S)
    if m:
        return f"**{m.group(1).strip()}** {m.group(2).strip()}".strip()
    return texto


def _cuerpo_markdown(art: Articulo, norma: Norma, reg: Registry) -> str:
    etq = norma.etiqueta_nota
    partes: list[str] = []
    bloques = art.bloques
    for i, b in enumerate(bloques):
        if b.tipo == "nota":
            partes.append(_render_nota(b, reg))
            continue
        texto = enlazar(b.texto, etq, reg)
        # Tachado: si el siguiente bloque es una nota de derogatoria/inexequibilidad.
        sig = bloques[i + 1] if i + 1 < len(bloques) else None
        if sig and sig.tipo == "nota" and sig.clase_nota == "warning":
            texto = f"~~{texto}~~"
        if b.tipo == "numeral":
            partes.append(f"{b.marca}. {texto}")
        elif b.tipo == "literal":
            partes.append(f"{b.marca}) {texto}")
        elif b.tipo == "paragrafo":
            partes.append(_render_paragrafo(texto))
        else:
            partes.append(texto)
    return "\n\n".join(partes)


def _render_articulo(art: Articulo, norma: Norma, reg: Registry) -> str:
    titulo = art.epigrafe or f"Artículo {art.numero}"
    cuerpo = _cuerpo_markdown(art, norma, reg)
    return f"{_frontmatter(art, norma)}\n\n## {titulo}\n\n{cuerpo}\n"


def render(norma: Norma, destino: str | Path, reg: Registry) -> dict:
    """Escribe la norma bajo ``destino/<etiqueta>/…``. Devuelve estadísticas."""
    raiz = Path(destino) / _slug(norma.etiqueta_nota)
    raiz.mkdir(parents=True, exist_ok=True)

    # Nota índice (preámbulo: encabezado, fecha, "DECRETA").
    if norma.preambulo:
        intro = "\n\n".join(enlazar(b.texto, norma.etiqueta_nota, reg) for b in norma.preambulo)
        encabezado = norma.titulo or norma.nombre_canonico
        (raiz / f"art. INTRO {_slug(norma.etiqueta_nota)}.md").write_text(
            f"# {encabezado}\n\n{intro}\n", encoding="utf-8"
        )

    pila: list[tuple[int, Nivel, Path]] = []  # (profundidad, nivel, carpeta)
    contadores: dict[str, int] = {}
    n_art = 0

    for it in norma.items:
        if isinstance(it, Nivel):
            while pila and pila[-1][0] >= it.profundidad:
                pila.pop()
            contadores[it.tipo] = contadores.get(it.tipo, 0) + 1
            padre = pila[-1][2] if pila else raiz
            carpeta = padre / _nombre_carpeta(contadores[it.tipo], it)
            carpeta.mkdir(parents=True, exist_ok=True)
            pila.append((it.profundidad, it, carpeta))
        elif isinstance(it, Articulo):
            carpeta = pila[-1][2] if pila else raiz
            archivo = carpeta / f"art. {it.numero} {_slug(norma.etiqueta_nota)}.md"
            archivo.write_text(_render_articulo(it, norma, reg), encoding="utf-8")
            n_art += 1

    return {
        "raiz": str(raiz),
        "articulos": n_art,
        "niveles": sum(contadores.values()),
    }
