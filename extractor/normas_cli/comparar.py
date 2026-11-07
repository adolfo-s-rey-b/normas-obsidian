"""Comparación de una norma entre dos fuentes (DAFP y Secretaría del Senado).

Las dos fuentes deberían coincidir, pero cada editor actualiza en fechas
distintas y con criterios propios. Este módulo alinea los artículos por número,
compara su **texto normativo** (sin notas, tachados ni puntuación) y produce un
informe con:

* fecha de actualización declarada por cada fuente;
* artículos idénticos, con diferencias y presentes solo en una fuente;
* las diferencias más grandes, con un extracto.

La decisión de cambiar la fuente principal de una norma se toma a partir de
este informe (``fuente`` en ``registry.yaml``); no se fusionan automáticamente
textos de editores distintos.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass

from .model import Norma

URL_SENADO = "http://www.secretariasenado.gov.co/senado/basedoc/"
# Nombres de archivo del Senado para las normas que no siguen el patrón ley_NNNN_AAAA.
SENADO_CONOCIDAS = {
    "CPol": "constitucion_politica_1991.html",
    "CCo": "codigo_comercio.html",
    "CST": "codigo_sustantivo_trabajo.html",
    "ET": "estatuto_tributario.html",
    "CPT": "codigo_procedimiento_laboral.html",
    "CC": "codigo_civil.html",
}


def url_senado(sigla: str | None, tipo: str | None, numero: str | None, anio: str | None) -> str | None:
    if sigla in SENADO_CONOCIDAS:
        return URL_SENADO + SENADO_CONOCIDAS[sigla]
    if tipo and tipo.lower().startswith("ley") and numero and anio and numero.isdigit():
        return f"{URL_SENADO}ley_{int(numero):04d}_{anio}.html"
    return None


def _normalizar(texto: str) -> str:
    texto = re.sub(r"~~.*?~~", " ", texto)  # apartes tachados (no vigentes)
    texto = re.sub(r"<[^<>]{0,600}>", " ", texto)  # marcas editoriales «<…>»
    texto = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^\w]+", " ", texto.lower())
    texto = re.sub(r"\b(\d+)\s?[oº°]\b", r"\1", texto)  # ordinales: «1o» = «1»
    return " ".join(texto.split())


def texto_articulos(norma: Norma) -> dict[str, str]:
    out = {}
    for a in norma.articulos:
        cuerpo = " ".join(b.texto for b in a.bloques if b.tipo not in ("nota", "tabla"))
        out[a.numero] = _normalizar(cuerpo)
    return out


RE_REFORMA_NOTA = re.compile(
    r"(?:modificad|adicionad|derogad|sustituid|subrogad)\w*\s+por\s+(?:el\s+|los\s+)?(?:art[íi]culo|art\.)?"
    r"[^.;]{0,80}?\b((?:Ley|Decreto|Acto Legislativo)\s+(?:Ley\s+|Nacional\s+)?(\d+)\s+de\s+(\d{4}))",
    re.I,
)


def reformas(norma: Norma) -> dict[str, int]:
    """Normas reformatorias citadas en notas/marcas: {«Ley 2445 de 2025»: año}."""
    out: dict[str, int] = {}
    for a in norma.articulos:
        for b in a.bloques + a.notas_cabecera:
            for m in RE_REFORMA_NOTA.finditer(b.texto):
                tipo = m.group(1).split()[0].capitalize()
                out[f"{tipo} {int(m.group(2))} de {m.group(3)}"] = int(m.group(3))
    return out


def reforma_mas_reciente(norma: Norma) -> int | None:
    r = reformas(norma)
    return max(r.values()) if r else None


@dataclass
class Diferencia:
    numero: str
    similitud: float
    extracto: str


@dataclass
class Comparacion:
    nombre_a: str
    nombre_b: str
    fecha_a: str | None
    fecha_b: str | None
    identicos: int
    diferentes: list[Diferencia]
    solo_a: list[str]
    solo_b: list[str]
    reforma_a: int | None = None
    reforma_b: int | None = None
    reformas_solo_a: list[str] | None = None
    reformas_solo_b: list[str] | None = None

    @property
    def total_comunes(self) -> int:
        return self.identicos + len(self.diferentes)


def comparar(a: Norma, b: Norma, nombre_a: str = "DAFP", nombre_b: str = "Senado") -> Comparacion:
    ta, tb = texto_articulos(a), texto_articulos(b)
    identicos, difs = 0, []
    for num in ta.keys() & tb.keys():
        x, y = ta[num], tb[num]
        if x == y:
            identicos += 1
            continue
        sm = difflib.SequenceMatcher(None, x.split(), y.split(), autojunk=False)
        ratio = sm.ratio()
        if ratio >= 0.995:
            identicos += 1
            continue
        partes = []
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op != "equal":
                xa = " ".join(x.split()[i1:i2])[:80]
                yb = " ".join(y.split()[j1:j2])[:80]
                partes.append(f"«{xa}» → «{yb}»")
            if len(partes) == 2:
                break
        difs.append(Diferencia(num, ratio, "; ".join(partes)))
    difs.sort(key=lambda d: d.similitud)
    orden = lambda s: [(0, int(t), "") if t.isdigit() else (1, 0, t) for t in re.findall(r"\d+|\D+", s)]  # noqa: E731
    return Comparacion(nombre_a, nombre_b, a.actualizacion_fuente, b.actualizacion_fuente, identicos, difs,
                       sorted(ta.keys() - tb.keys(), key=orden), sorted(tb.keys() - ta.keys(), key=orden),
                       reforma_mas_reciente(a), reforma_mas_reciente(b),
                       *_solo(reformas(a), reformas(b)))


def _solo(ra: dict[str, int], rb: dict[str, int]) -> tuple[list[str], list[str]]:
    clave = lambda k: (-ra.get(k, rb.get(k, 0)), k)  # noqa: E731
    return sorted(ra.keys() - rb.keys(), key=clave), sorted(rb.keys() - ra.keys(), key=clave)


def informe(c: Comparacion, titulo: str, *, max_dif: int = 25) -> str:
    pct = 100 * c.identicos / c.total_comunes if c.total_comunes else 0
    lineas = [
        f"# Comparación de fuentes — {titulo}",
        "",
        "| | " + c.nombre_a + " | " + c.nombre_b + " |",
        "| --- | --- | --- |",
        f"| Actualización declarada | {c.fecha_a or '—'} | {c.fecha_b or '—'} |",
        f"| Reforma más reciente citada | {c.reforma_a or '—'} | {c.reforma_b or '—'} |",
        f"| Artículos | {c.total_comunes + len(c.solo_a)} | {c.total_comunes + len(c.solo_b)} |",
        f"| Solo en esta fuente | {len(c.solo_a)} | {len(c.solo_b)} |",
        "",
        f"Artículos en ambas: {c.total_comunes}; texto idéntico: {c.identicos} ({pct:.1f} %); "
        f"con diferencias: {len(c.diferentes)}.",
        "",
    ]
    for nombre, lista in ((c.nombre_a, c.reformas_solo_a), (c.nombre_b, c.reformas_solo_b)):
        if lista:
            lineas += [f"Reformas citadas solo por {nombre}: " + ", ".join(lista[:12])
                       + (" …" if len(lista) > 12 else ""), ""]
    if c.solo_a:
        lineas += [f"Solo en {c.nombre_a}: " + ", ".join(c.solo_a[:60]) + (" …" if len(c.solo_a) > 60 else ""), ""]
    if c.solo_b:
        lineas += [f"Solo en {c.nombre_b}: " + ", ".join(c.solo_b[:60]) + (" …" if len(c.solo_b) > 60 else ""), ""]
    if c.diferentes:
        lineas += ["## Diferencias más grandes", "", "| Art. | Similitud | Extracto |", "| --- | ---: | --- |"]
        for d in c.diferentes[:max_dif]:
            lineas.append(f"| {d.numero} | {d.similitud:.0%} | {d.extracto.replace('|', '/')} |")
    return "\n".join(lineas) + "\n"
