"""Motor de wikilinks: convierte referencias a artículos en enlaces de Obsidian.

Estrategia (ver plan): para cada mención "artículo(s) N…" se examina la cláusula
siguiente para hallar el *marcador de norma destino*:

  * sin marcador / "de este código" / "de la presente ley" / "ibídem"  → misma norma
  * "del Código de Comercio"                                           → sigla del registro
  * "de la Ley 1996 de 2019" / "del Decreto 1429 de 2020"              → "Ley 1996 de 2019"

Cada número se reemplaza por ``[[art. N <ETIQUETA>|N]]`` preservando el texto
visible. Los números del propio marcador (p. ej. el año de la ley) no se enlazan.
"""

from __future__ import annotations

import re

from .registry import Registry, _norm

RE_REF = re.compile(r"\bart[íi]culos?\b\.?", re.I)
RE_NUM = re.compile(r"\b\d+[A-Za-z]?(?:-\d+)?\b")

# Marcadores que apuntan a la MISMA norma. Nota: "de[l]?" cubre la contracción
# "del" (= de + el), frecuente en "del Código…", "del presente código".
RE_MISMA = re.compile(
    r"\bde[l]?\s+(?:est[ae]|(?:la|el)\s+presente|presente)\s+(?:c[óo]digo|ley)\b"
    r"|\bib[ií]dem\b",
    re.I,
)
# Marcador de norma externa identificada (Ley/Decreto/Resolución N de A).
RE_EXT_NUMERADA = re.compile(
    r"\bde[l]?\s+(?:la\s+|el\s+)?(Ley|Decreto(?:\s+Ley)?|Resoluci[óo]n|Acuerdo)\s+"
    r"(\d+[A-Za-z]?)\s+de\s+(\d{4})",
    re.I,
)
# Marcador de código nombrado: "del Código de Comercio", "del Código Civil"…
RE_EXT_CODIGO = re.compile(
    r"\bde[l]?\s+(?:la\s+|el\s+)?(C[óo]digo(?:\s+[A-Za-zÁÉÍÓÚáéíóúÑñ]+){1,5})",
    re.I,
)


def _clausula_fin(texto: str, inicio: int) -> int:
    m = re.search(r"[.;:]\s|\n", texto[inicio:])
    fin = inicio + m.start() if m else len(texto)
    return min(fin, inicio + 240)


def _resolver_marcador(
    clausula: str, etiqueta_actual: str, reg: Registry
) -> tuple[str, int]:
    """Devuelve ``(etiqueta_destino, pos_marcador)`` para una cláusula.

    ``pos_marcador`` es el índice donde empieza el marcador externo (los números
    a partir de ahí no se enlazan); ``len(clausula)`` si no hay marcador externo.
    """
    m_ext = RE_EXT_NUMERADA.search(clausula)
    m_cod = RE_EXT_CODIGO.search(clausula)
    m_mis = RE_MISMA.search(clausula)

    candidatos = []
    if m_ext:
        etq = reg.etiqueta_por_id("", m_ext.group(0)) or (
            f"{m_ext.group(1).title()} {m_ext.group(2)} de {m_ext.group(3)}"
        )
        candidatos.append((m_ext.start(), etq))
    if m_cod:
        sigla = reg.sigla_de_codigo(m_cod.group(1))
        etq = sigla or m_cod.group(1).strip()
        candidatos.append((m_cod.start(), etq))
    if m_mis:
        candidatos.append((m_mis.start(), etiqueta_actual))

    if not candidatos:
        return etiqueta_actual, len(clausula)
    # El marcador relevante es el primero tras los números.
    pos, etq = min(candidatos, key=lambda c: c[0])
    return etq, pos


def _wikilink(num: str, etiqueta: str) -> str:
    return f"[[art. {num} {etiqueta}|{num}]]"


def enlazar(texto: str, etiqueta_actual: str, reg: Registry) -> str:
    """Inserta wikilinks en las referencias a artículos de ``texto``."""
    salida = []
    pos = 0
    for m in RE_REF.finditer(texto):
        if m.start() < pos:
            continue
        salida.append(texto[pos:m.end()])  # texto previo + "artículo(s)"
        ini = m.end()
        fin = _clausula_fin(texto, ini)
        clausula = texto[ini:fin]
        etq, pos_marc = _resolver_marcador(clausula, etiqueta_actual, reg)
        # Enlazamos los números que están antes del marcador externo.
        zona = clausula[:pos_marc]
        resto = clausula[pos_marc:]
        zona_enl = RE_NUM.sub(lambda mm: _wikilink(mm.group(0), etq), zona)
        salida.append(zona_enl + resto)
        pos = fin
    salida.append(texto[pos:])
    return "".join(salida)


def enlace_de_href(i: str, art: str | None, texto_ancla: str, reg: Registry) -> str | None:
    """Construye un wikilink a partir de un ``<a href="norma.php?i=..#art">``."""
    etq = reg.etiqueta_por_id(i, texto_ancla)
    if not etq or not art:
        return None
    return f"[[art. {art} {etq}]]"
