"""Control de calidad de una biblioteca generada.

Errores (código de salida 1):
  * notas con el mismo nombre (Obsidian no distingue mayúsculas) — los
    wikilinks serían ambiguos;
  * alias que apuntan a notas distintas;
  * carpetas vacías.

Advertencias (errores solo con ``--estricto``):
  * enlaces a artículos de una norma presente en la biblioteca que no existen;
  * artículos sin texto en la fuente.

También resume los enlaces a normas que aún no están en la biblioteca.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

import yaml

RE_LINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")


def frontmatter(texto: str) -> dict:
    if not texto.startswith("---\n"):
        return {}
    fin = texto.find("\n---", 4)
    if fin < 0:
        return {}
    try:
        return yaml.safe_load(texto[4:fin]) or {}
    except yaml.YAMLError:
        return {}


def verificar(biblioteca: Path, *, estricto: bool = False, salida=print) -> int:
    notas = sorted(biblioteca.rglob("*.md"))
    nombres: dict[str, list[Path]] = defaultdict(list)
    alias: dict[str, set[Path]] = defaultdict(set)
    datos: dict[Path, tuple[dict, str]] = {}
    for p in notas:
        txt = p.read_text(encoding="utf-8")
        fm = frontmatter(txt)
        datos[p] = (fm, txt)
        nombres[p.stem.lower()].append(p)
        for a in fm.get("aliases") or []:
            alias[str(a).lower()].add(p)

    errores = 0
    dup = {k: v for k, v in nombres.items() if len(v) > 1}
    for k, v in list(dup.items())[:20]:
        salida(f"✗ nombre duplicado «{k}»: " + ", ".join(str(x.relative_to(biblioteca)) for x in v))
    errores += len(dup)

    choques = {a: ps for a, ps in alias.items() if len(ps) > 1 or (a in nombres and nombres[a][0] not in ps)}
    for a, ps in list(choques.items())[:20]:
        salida(f"✗ alias ambiguo «{a}»: " + ", ".join(str(x.relative_to(biblioteca)) for x in ps))
    errores += len(choques)

    vacias = [d for d in biblioteca.rglob("*") if d.is_dir() and not any(d.iterdir())]
    for d in vacias[:20]:
        salida(f"✗ carpeta vacía: {d.relative_to(biblioteca)}")
    errores += len(vacias)

    # Normas presentes: etiqueta = parte final de «art. N <ETIQUETA>».
    resolubles = set(nombres) | set(alias)
    etiquetas_presentes: set[str] = set()
    for p, (fm, _) in datos.items():
        if fm.get("tipo") == "norma":
            etiquetas_presentes.add(p.stem)
            etiquetas_presentes.update(str(a) for a in fm.get("aliases") or [])

    rotos_internos: Counter = Counter()
    ejemplos: dict[str, str] = {}
    externos: Counter = Counter()
    for p, (fm, txt) in datos.items():
        for m in RE_LINK.finditer(txt):
            destino = m.group(1).strip()
            if destino.lower() in resolubles:
                continue
            mm = re.match(r"art\. (?:transitorio )?[\w-]+(?: \([^)]*\))?(?: \d+)? (.+)$", destino)
            etq = mm.group(1) if mm else destino
            if etq in etiquetas_presentes:
                rotos_internos[etq] += 1
                ejemplos.setdefault(etq, f"{p.relative_to(biblioteca)} → [[{destino}]]")
            else:
                externos[etq] += 1

    vacios = [p for p, (fm, txt) in datos.items()
              if fm.get("tipo") == "articulo" and "*(Sin texto en la fuente.)*" in txt]

    n_art = sum(1 for fm, _ in datos.values() if fm.get("tipo") == "articulo")
    salida(f"Notas: {len(notas)} · artículos: {n_art} · normas: "
           f"{sum(1 for fm, _ in datos.values() if fm.get('tipo') == 'norma')}")
    if rotos_internos:
        salida(f"{'✗' if estricto else '!'} enlaces internos rotos: {sum(rotos_internos.values())}")
        for etq, n in rotos_internos.most_common():
            salida(f"    {etq}: {n}  (p. ej. {ejemplos[etq]})")
    if vacios:
        salida(f"{'✗' if estricto else '!'} artículos sin texto en la fuente: {len(vacios)}")
    if externos:
        salida("· enlaces a normas fuera de la biblioteca: "
               + ", ".join(f"{e} ({n})" for e, n in externos.most_common(12))
               + (" …" if len(externos) > 12 else ""))
    if estricto:
        errores += sum(rotos_internos.values()) + len(vacios)
    salida("✓ biblioteca sin errores" if not errores else f"✗ {errores} errores")
    return 1 if errores else 0
