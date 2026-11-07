"""Motor de wikilinks: convierte referencias a artículos en enlaces de Obsidian.

Para cada mención «artículo(s) …» / «art. …» se toma la cláusula siguiente
(hasta «. », «; » o «: ») y se localizan en ella los *marcadores de norma*:

  * numerados: «Ley 1996 de 2019», «Decreto Nacional 1736 de 2012» (con
    cualquier preposición: de, del, en, por, según…) → sigla del registry o
    nombre normalizado («Decreto 1736 de 2012»);
  * códigos con nombre: «del Código de Comercio» → sigla del diccionario
    ``codigos`` (gana la coincidencia más larga). Un «Código X» desconocido
    **no** se enlaza;
  * misma norma: «de este código», «de la presente ley», «ibídem».

Los números que preceden a cada marcador se enlazan a esa norma; los que no
tienen marcador, a la norma actual. Solo se enlazan números en modo
«artículo»: tras «numeral», «inciso», «literal», «parágrafo»… se dejan como
texto. Cada número se reemplaza por ``[[art. N <ETIQUETA>|N]]``.
"""

from __future__ import annotations

import re
import unicodedata

from .registry import RE_IDENTIDAD, Registry

RE_REF = re.compile(r"\b(?:art[íi]culos?|arts?\.)(?=\s|\d)", re.I)

RE_MISMA = re.compile(
    r"\b(?:de|del|en|por)\s+(?:est[ae]|(?:la|el)\s+presente|presente)\s+"
    r"(?:c[óo]digo|ley|estatuto|decreto|constituci[óo]n|acto\s+legislativo)\b"
    r"|\bib[íi]dem\b|\bejusdem\b",
    re.I,
)
# Referencias anafóricas a otra norma ya mencionada: no se puede resolver.
RE_ANAFORA = re.compile(
    r"\b(?:del?|de\s+la|en\s+el|en\s+la)\s+(?:citad[oa]|mism[oa]|dich[oa]|mencionad[oa]|referid[oa])\s+"
    r"(?:c[óo]digo|ley|decreto|estatuto|norma|resoluci[óo]n)\b",
    re.I,
)
# «Código X» con mayúscula que no esté en el diccionario: corta el enlazado.
RE_CODIGO_DESCONOCIDO = re.compile(r"\bC[óo]digo\s+(?:de\s+|del\s+|de\s+la\s+)?[A-ZÁÉÍÓÚ]\w+")

RE_TOKEN = re.compile(
    r"(?P<kw>\b(?:art[íi]culos?|arts?\.|transitorios?|numeral(?:es)?|incisos?|literal(?:es)?|"
    r"ordinal(?:es)?|par[áa]grafos?|cap[íi]tulos?|t[íi]tulos?|libros?|secci[óo]n(?:es)?|"
    r"leyes|ley|decretos?|sentencias?|n[uú]meros?|n[°º]|resoluci[óo]n(?:es)?|"
    r"inc\.|num\.|lit\.|par\.|ord\.|parag\.)(?=\W|$))"
    r"|(?P<num>(?<![\w.,$-])\d+(?-i:[A-NP-Z])?(?:-\d+)?)(?=[º°]|o\b|\b)(?![.,]\d)",
    re.I,
)
# Lo que puede separar dos números de una misma enumeración de artículos.
RE_ENUM = re.compile(
    r"^(?:[\s,;()]|[º°]|o\b|\.(?=\s)|\b(?:y|e|o|u|al|a|hasta|el|los|del|de\s+los|"
    r"N[°º]\.?|No\.)\b)*$",
    re.I,
)
RE_FECHA = re.compile(
    r"\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|"
    r"setiembre|octubre|noviembre|diciembre)\b",
    re.I,
)
RE_REFORMA = re.compile(r"(?:quedar[áa]n?\s+)?as[íi]\s*:\s*", re.I)
RE_VERBO_REFORMA = re.compile(
    r"\b(?:modif[íi]quese|modif[íi]case|adici[óo]nese|sustit[úu]yase|subr[óo]guese|reempl[áa]cese|"
    r"quedar[áa]n?)\b",
    re.I,
)


def _fold(s: str) -> str:
    out = []
    for c in s:
        d = unicodedata.normalize("NFD", c)[0].lower() if c.strip() else c
        out.append(d if len(d) == 1 else c)
    return "".join(out)


_cache_codigos: dict[int, re.Pattern | None] = {}


def _re_codigos(reg: Registry) -> re.Pattern | None:
    clave = id(reg)
    if clave not in _cache_codigos:
        nombres = reg.nombres_de_codigos()
        _cache_codigos[clave] = (
            re.compile(r"\b(" + "|".join(re.escape(n) for n in nombres) + r")\b")
            if nombres else None
        )
    return _cache_codigos[clave]


def marcadores(texto: str, etiqueta_actual: str | None, reg: Registry) -> list[tuple[int, int, str | None]]:
    """Marcadores de norma en ``texto``: ``(inicio, fin, etiqueta|None)``.

    ``None`` significa «norma desconocida»: los números previos no se enlazan.
    """
    hallados: list[tuple[int, int, str | None]] = []
    for m in RE_IDENTIDAD.finditer(texto):
        hallados.append((m.start(), m.end(), reg.etiqueta_por_identidad(m.group(1), m.group(2), m.group(3))))
    for m in re.finditer(r"\bde\s+la\s+(\d{2,4})\s+de\s+(\d{4})\b", texto):
        hallados.append((m.start(), m.end(), reg.etiqueta_por_identidad("Ley", m.group(1), m.group(2))))
    rc = _re_codigos(reg)
    if rc is not None:
        for m in rc.finditer(_fold(texto)):
            hallados.append((m.start(), m.end(), reg.codigos[m.group(1)]))
    for m in RE_CODIGO_DESCONOCIDO.finditer(texto):
        hallados.append((m.start(), m.end(), None))
    for m in RE_MISMA.finditer(texto):
        hallados.append((m.start(), m.end(), etiqueta_actual))
    for m in RE_ANAFORA.finditer(texto):
        hallados.append((m.start(), m.end(), None))
    # Sin solapamientos: el que empieza antes; a igual inicio, el más largo y
    # los conocidos antes que los desconocidos.
    hallados.sort(key=lambda h: (h[0], -(h[1] - h[0]), h[2] is None))
    out: list[tuple[int, int, str | None]] = []
    for h in hallados:
        if out and h[0] < out[-1][1]:
            continue
        out.append(h)
    return out


LIMITE_CLAUSULA = 700


def _clausula_fin(texto: str, inicio: int) -> tuple[int, bool]:
    """Fin de la cláusula y si es un fin natural (no truncado por longitud)."""
    for m in re.finditer(r"[.;:](?=\s|$)|\n", texto[inicio:]):
        antes = texto[max(0, inicio + m.start() - 4): inicio + m.start()]
        if m.group() == "." and re.search(r"(?:\bart|\barts|\bNo|\bnum|\bLit|\bInc)$", antes, re.I):
            continue
        if m.start() > LIMITE_CLAUSULA:
            break
        return inicio + m.start(), True
    if len(texto) - inicio <= LIMITE_CLAUSULA:
        return len(texto), True
    return inicio + LIMITE_CLAUSULA, False


def _wikilink(num: str, etiqueta: str, transitorio: bool = False) -> str:
    destino = f"transitorio {num}" if transitorio else num
    return f"[[art. {destino} {etiqueta}|{num}]]"


def _enlazar_zona(zona: str, etiqueta: str | None, modo: str = "art") -> tuple[str, str]:
    """Enlaza los números de ``zona`` que están en modo «artículo»."""
    if etiqueta is None:
        return zona, modo
    out, pos = [], 0
    ultimo = 0  # fin de la última palabra clave o número en modo «artículo»
    for m in RE_TOKEN.finditer(zona):
        if m.group("kw"):
            kw = m.group("kw").lower()
            if kw.startswith("art"):
                modo = "art"
            elif kw.startswith("transitorio"):
                modo = "trans" if modo in ("art", "trans") else modo
            else:
                modo = "otro"
            ultimo = m.end()
            continue
        if modo not in ("art", "trans") or RE_FECHA.match(zona, m.end()):
            continue
        if not RE_ENUM.match(zona[ultimo:m.start()]):
            modo = "otro"  # el número ya no forma parte de la enumeración
            continue
        ultimo = m.end()
        out.append(zona[pos:m.start()])
        out.append(_wikilink(m.group("num"), etiqueta, modo == "trans"))
        pos = m.end()
    out.append(zona[pos:])
    return "".join(out), modo


def enlazar(texto: str, etiqueta_actual: str | None, reg: Registry) -> str:
    """Inserta wikilinks en las referencias a artículos de ``texto``."""
    salida, pos = [], 0
    for m in RE_REF.finditer(texto):
        if m.start() < pos:
            continue
        if m.group().isupper() and re.match(r"\s+\d+[A-Z]?(?:-\d+)?\s*[º°o]?\s*\.\s", texto[m.end():]):
            continue
        salida.append(texto[pos:m.end()])
        ini = m.end()
        fin, natural = _clausula_fin(texto, ini)
        clausula = texto[ini:fin]
        marcs = marcadores(clausula, etiqueta_actual, reg)
        if not marcs and not natural:
            # Enumeración demasiado larga para saber a qué norma pertenece.
            salida.append(clausula)
            pos = fin
            continue
        cursor, modo, partes = 0, "art", []
        for (a, b, etq) in marcs:
            zona_enl, modo = _enlazar_zona(clausula[cursor:a], etq, modo)
            partes.append(zona_enl + clausula[a:b])
            cursor, modo = b, "art"
        cola = clausula[cursor:]
        if not marcs:
            cola, _ = _enlazar_zona(cola, etiqueta_actual, "art")
        elif re.search(r"\bart[íi]culos?\b", cola, re.I):
            # Nueva referencia tras el último marcador, sin marcador propio.
            cola, _ = _enlazar_zona(cola, etiqueta_actual, "otro")
        partes.append(cola)
        salida.append("".join(partes))
        pos = fin
    salida.append(texto[pos:])
    return "".join(salida)


def objetivo_de_reforma(texto: str, etiqueta_actual: str | None, reg: Registry) -> tuple[str, int] | None:
    """Si ``texto`` introduce el texto de una norma reformada («Modifíquese el
    artículo 577 de la Ley 1564 de 2012, así: "…"» / «…el cual quedará así:»),
    devuelve ``(etiqueta de la norma reformada, posición donde empieza la cita)``.
    """
    for m in RE_REFORMA.finditer(texto):
        previo = texto[:m.start()]
        if not RE_VERBO_REFORMA.search(previo):
            continue
        externos = [e for (_, _, e) in marcadores(previo, etiqueta_actual, reg)
                    if e and e != etiqueta_actual]
        if externos:
            return externos[-1], m.end()
    return None


def enlazar_bloque(texto: str, etiqueta: str | None, reg: Registry) -> tuple[str, str | None]:
    """Enlaza un párrafo y detecta si abre una cita de otra norma.

    Devuelve ``(texto enlazado, etiqueta para los párrafos siguientes o None)``.
    """
    obj = objetivo_de_reforma(texto, etiqueta, reg)
    if not obj:
        return enlazar(texto, etiqueta, reg), None
    destino, corte = obj
    return enlazar(texto[:corte], etiqueta, reg) + enlazar(texto[corte:], destino, reg), destino
