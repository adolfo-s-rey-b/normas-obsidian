"""Consolidación multifuente: una norma a partir de todas sus fuentes.

Cada norma puede estar publicada por varias fuentes (Gestor Normativo del DAFP,
Secretaría General del Senado…) que se actualizan en fechas distintas y con
criterios propios. Ninguna gana siempre: difieren artículo por artículo. Este
módulo produce **una** :class:`Norma` con la versión más actualizada de cada
artículo:

1. **Base estructural** (jerarquía, preámbulo, firmas, orden): la fuente
   preferida (el Senado) si cubre al menos el 95 % de los artículos de la fuente
   más completa; si no, la más completa.
2. **Por artículo** se elige la versión cuya nota de reforma más reciente
   (``Modificado por … Ley N de AAAA``) sea posterior. Empate → la base. Una
   versión sin texto normativo nunca reemplaza a otra que sí lo tiene.
3. Los artículos que solo están en una fuente se insertan en su lugar.

Cada artículo queda marcado con su fuente, la reforma más reciente citada y si
el texto coincide entre fuentes; la norma guarda un resumen de la comparación.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .comparar import RE_REFORMA_NOTA, _normalizar
from .model import Articulo, Norma

PREFERIDA = "Senado"


@dataclass
class Fuente:
    nombre: str  # "DAFP", "Senado"
    url: str | None
    norma: Norma
    tachado_explicito: bool = False


# Sentencias de constitucionalidad: «C-038-25», «C-038 de 2025», «Sentencia SU-123/19».
RE_SENTENCIA = re.compile(r"\b(?:C|SU)-\d{1,4}(?:\s*[-/]\s*(\d{2})\b|\s+de\s+(\d{4}))")


def _anio_sentencia(m: re.Match) -> int:
    if m.group(2):
        return int(m.group(2))
    yy = int(m.group(1))
    return 1900 + yy if yy >= 91 else 2000 + yy


def reforma_de(a: Articulo) -> int | None:
    """Año del evento de vigencia más reciente citado en las notas del artículo:
    reformas (modificado/adicionado/derogado por Ley…) y sentencias de la Corte
    Constitucional (una inexequibilidad posterior puede revivir el texto anterior)."""
    anios = []
    for b in [x for x in a.bloques if x.tipo == "nota"] + a.notas_cabecera:
        anios += [int(m.group(3)) for m in RE_REFORMA_NOTA.finditer(b.texto)]
        anios += [_anio_sentencia(m) for m in RE_SENTENCIA.finditer(b.texto)]
    anios = [x for x in anios if 1880 <= x <= 2100]
    return max(anios) if anios else None


def _texto(a: Articulo) -> str:
    return _normalizar(" ".join(b.texto for b in a.bloques if b.tipo not in ("nota", "tabla")))


def _clave(numero: str) -> tuple:
    """Orden de un número de artículo: transitorios al final, «115-1» tras «115»."""
    trans = numero.startswith("transitorio")
    nums = [int(x) for x in re.findall(r"\d+", numero)] or [0]
    letra = re.search(r"\d([A-Z])\b", numero)
    return (1 if trans else 0, *nums[:6], *([0] * (6 - len(nums[:6]))), letra.group(1) if letra else "")


def elegir_base(fuentes: list[Fuente]) -> Fuente:
    maximo = max(len(f.norma.articulos) for f in fuentes)
    pref = next((f for f in fuentes if f.nombre == PREFERIDA), None)
    if pref is not None and len(pref.norma.articulos) >= 0.95 * maximo:
        return pref
    return max(fuentes, key=lambda f: len(f.norma.articulos))


def consolidar(fuentes: list[Fuente]) -> Norma:
    """Una sola :class:`Norma` con la versión más actualizada de cada artículo."""
    if len(fuentes) == 1:
        f = fuentes[0]
        for a in f.norma.articulos:
            a.fuente, a.url_fuente, a.reforma = f.nombre, f.url, reforma_de(a)
            a.tachado_explicito = f.tachado_explicito
        return f.norma

    base = elegir_base(fuentes)
    por_fuente = {f.nombre: {a.numero: a for a in f.norma.articulos} for f in fuentes}
    elegidos: dict[str, int] = {f.nombre: 0 for f in fuentes}
    identicos = diferentes = 0
    detalle_dif: list[str] = []

    def mejor(numero: str) -> tuple[Articulo, Fuente]:
        nonlocal identicos, diferentes
        versiones = [(f, por_fuente[f.nombre][numero]) for f in fuentes if numero in por_fuente[f.nombre]]
        textos = {_texto(a) for _, a in versiones}
        con_texto = [(f, a) for f, a in versiones if _texto(a)] or versiones

        def puntaje(fa):
            f, a = fa
            return (reforma_de(a) or 0, 1 if f is base else 0)

        f, a = max(con_texto, key=puntaje)
        if len(versiones) > 1:
            if len(textos) == 1:
                identicos += 1
                a.coincidencia = "idéntico"
            else:
                diferentes += 1
                a.coincidencia = "difiere"
                if len(detalle_dif) < 400:
                    otras = ", ".join(f"{g.nombre} {reforma_de(b) or '—'}" for g, b in versiones)
                    detalle_dif.append(f"{numero}: se toma {f.nombre} ({otras})")
        else:
            a.coincidencia = f"solo en {f.nombre}"
        if not a.epigrafe:  # rúbrica de otra fuente si la elegida no la trae
            a.epigrafe = next((b.epigrafe for _, b in versiones if b.epigrafe), None)
        a.fuente, a.url_fuente, a.reforma = f.nombre, f.url, reforma_de(a)
        a.tachado_explicito = f.tachado_explicito
        elegidos[f.nombre] += 1
        return a, f

    norma = base.norma
    items: list = []
    vistos: set[str] = set()
    for it in norma.items:
        if isinstance(it, Articulo):
            a, _ = mejor(it.numero)
            items.append(a)
            vistos.add(it.numero)
        else:
            items.append(it)

    # Artículos que la base no tiene: se insertan tras el anterior en orden.
    extras = sorted({n for f in fuentes for n in por_fuente[f.nombre]} - vistos, key=_clave)
    for numero in extras:
        a, _ = mejor(numero)
        k = _clave(numero)
        pos = len(items)
        for i, it in enumerate(items):
            if isinstance(it, Articulo) and _clave(it.numero) > k:
                pos = i
                # retroceder sobre niveles que preceden al artículo siguiente
                while pos > 0 and not isinstance(items[pos - 1], Articulo):
                    pos -= 1
                break
        items.insert(pos, a)
        norma.avisos.append(f"artículo {numero} tomado solo de {a.fuente}")
    norma.items = items

    # Identidad y metadatos: completar con las demás fuentes.
    for f in fuentes:
        if f is base:
            continue
        for campo in ("tipo", "numero", "anio", "fecha", "epigrafe_norma", "id_fuente"):
            if not getattr(norma, campo) and getattr(f.norma, campo):
                setattr(norma, campo, getattr(f.norma, campo))
    norma.consolidacion = {
        "base": base.nombre,
        "fuentes": [{"nombre": f.nombre, "url": f.url, "articulos": len(f.norma.articulos),
                     "actualizacion": f.norma.actualizacion_fuente} for f in fuentes],
        "elegidos": elegidos,
        "identicos": identicos,
        "diferentes": diferentes,
        "solo_una": sum(1 for a in norma.articulos if (a.coincidencia or "").startswith("solo")),
        "detalle": detalle_dif,
    }
    return norma
