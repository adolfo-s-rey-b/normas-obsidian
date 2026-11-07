"""Renderiza una :class:`Norma` a la estructura de carpetas/notas de Obsidian.

Estructura generada bajo ``destino/<ETIQUETA>/``::

    CGP.md                                  ← nota raíz: metadatos, preámbulo,
                                              tabla de contenido, firmas
    1. LIBRO PRIMERO - SUJETOS DEL PROCESO/
        CGP - Libro Primero.md              ← nota índice del nivel
        1. SECCIÓN PRIMERA - …/
            …/art. 15 CGP.md                ← un artículo por nota

Cada artículo lleva frontmatter con alias (sigla e identificador), ubicación
jerárquica, vigencia, normas que lo modifican/derogan, fuente y navegación
(anterior/siguiente). La escritura es atómica por norma: se genera en un
directorio temporal y luego reemplaza la carpeta anterior, para no dejar notas
obsoletas.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .fetch import url_para_id
from .links import enlazar, enlazar_bloque, marcadores
from .model import Articulo, Bloque, Nivel, Norma
from .registry import Registry, _norm, nombre_normalizado

_INVALIDOS = re.compile(r'[\\/:*?"<>|#^\[\]]+')


def slug(texto: str, *, limite: int = 110) -> str:
    """Nombre de archivo válido; corta en límite de palabra."""
    texto = _INVALIDOS.sub("-", texto)
    texto = re.sub(r"\s+", " ", texto).strip().strip(".").strip()
    if len(texto) <= limite:
        return texto
    corte = texto[:limite]
    if " " in corte[limite // 2:]:
        corte = corte[: corte.rfind(" ")]
    return corte.rstrip(" ,;-–") + "…"


def _q(s: str) -> str:
    """Cadena YAML segura (JSON es YAML válido)."""
    return json.dumps(s, ensure_ascii=False)


def _tag(s: str) -> str:
    return re.sub(r"[^\w/-]+", "_", _norm(s)).strip("_")


_TIPO_CORTO = {"PARTE": "Parte", "LIBRO": "Libro", "TÍTULO": "Título", "SECCIÓN": "Sección",
               "CAPÍTULO": "Capítulo", "RUBRO": ""}
_CLAVE_FM = {"PARTE": "parte", "LIBRO": "libro", "TÍTULO": "titulo", "SECCIÓN": "seccion",
             "CAPÍTULO": "capitulo", "RUBRO": "rubro"}


def _etq_corta(n: Nivel) -> str:
    if n.tipo == "RUBRO":
        return slug(n.nombre.capitalize(), limite=50)
    eti = n.etiqueta.capitalize() if not re.fullmatch(r"[IVXLCDM]+[A-Z]?", n.etiqueta) else n.etiqueta
    return " ".join(x for x in (_TIPO_CORTO[n.tipo], eti) if x) or _TIPO_CORTO[n.tipo]


def _titulo_nivel(n: Nivel) -> str:
    if n.tipo == "RUBRO":
        return n.nombre
    base = " ".join(x for x in (n.tipo, n.etiqueta) if x)
    return f"{base} - {n.nombre}" if n.nombre else base


# --- Árbol -----------------------------------------------------------------------


@dataclass
class Nodo:
    nivel: Nivel | None
    padre: "Nodo | None" = None
    hijos: list = field(default_factory=list)  # Nodo | Articulo
    carpeta: Path | None = None
    nota: str = ""  # nombre (sin .md) de la nota índice

    @property
    def ancestros(self) -> list["Nodo"]:
        out, n = [], self
        while n is not None and n.nivel is not None:
            out.append(n)
            n = n.padre
        return list(reversed(out))

    def articulos(self) -> list[Articulo]:
        out: list[Articulo] = []
        for h in self.hijos:
            out.extend([h] if isinstance(h, Articulo) else h.articulos())
        return out


def _arbol(norma: Norma) -> Nodo:
    raiz = Nodo(None)
    pila = [raiz]
    for it in norma.items:
        if isinstance(it, Nivel):
            while len(pila) > 1 and pila[-1].nivel.profundidad >= it.profundidad:  # type: ignore[union-attr]
                pila.pop()
            nodo = Nodo(it, padre=pila[-1])
            pila[-1].hijos.append(nodo)
            pila.append(nodo)
        else:
            pila[-1].hijos.append(it)
    _podar_rubros(raiz)
    return raiz


def _podar_rubros(nodo: Nodo) -> None:
    """Quita los rubros sin artículos (encabezados sueltos de la fuente)."""
    for h in [h for h in nodo.hijos if isinstance(h, Nodo)]:
        _podar_rubros(h)
        if h.nivel is not None and h.nivel.tipo == "RUBRO" and not h.articulos():
            nodo.hijos.remove(h)


# --- Vigencia y notas ----------------------------------------------------------


RE_ART_COMPLETO = re.compile(
    r"\bart[íi]culo\s+(?:\w+\s+){0,4}?(?:derogad|declarad[oa]\s+inexequible|inexequible|suprimid)",
    re.I,
)


def _vigencia(art: Articulo, tachados: int, estado_norma: str | None) -> str:
    if estado_norma == "derogada":
        return "derogado"
    notas = [b for b in art.notas_cabecera + art.bloques if b.tipo == "nota"]
    contenido = [b for b in art.bloques if b.tipo != "nota"]
    for b in notas:
        t = b.texto.lower()
        if RE_ART_COMPLETO.search(b.texto) or (not contenido and b.clase_nota == "warning"):
            return "inexequible" if "inexequible" in t and "deroga" not in t else "derogado"
    if tachados:
        if any("inexequible" in b.texto.lower() for b in notas if b.clase_nota == "warning"):
            return "parcialmente inexequible"
        return "parcialmente derogado"
    if any(b.clase_nota == "info" for b in notas):
        return "modificado"
    return "vigente"


def _render_nota(b: Bloque, etiqueta: str, reg: Registry) -> str:
    texto = b.texto.strip()
    if texto.startswith("(") and texto.rstrip(" .").endswith(")"):
        texto = texto.rstrip(" .")[1:-1].strip()
    if re.match(r"(?:Ver|V[ée]ase|Concordancia)", texto, re.I):
        # «Ver Ley 143 de 1994; Art. 27»: los artículos son de la norma citada.
        marcs = marcadores(texto, etiqueta, reg)
        if marcs:
            etiqueta = marcs[0][2]
    texto = enlazar(texto, etiqueta, reg)
    if "[[" not in texto and re.search(r"\bart", texto, re.I):
        for h in b.hrefs:
            if h.i and h.art and h.art.isdigit():
                etq = reg.etiqueta_por_id(h.i, h.texto)
                if etq:
                    texto += f" ([[art. {h.art} {etq}]])"
                    break
    return f"> [!{b.clase_nota or 'note'}] {texto}"


def _render_paragrafo(texto: str) -> str:
    m = re.match(r"(par[áa]grafo[^.]{0,40}?\.)\s*(.*)$", texto, re.I | re.S)
    if m:
        return f"**{m.group(1).strip()}** {m.group(2).strip()}".strip()
    return texto


def _enlaces_en(texto: str) -> list[str]:
    return [f"[[{m.group(1)}]]" for m in re.finditer(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]", texto)]


# --- Renderizador ------------------------------------------------------------------


class Renderizador:
    def __init__(self, norma: Norma, reg: Registry, *, fecha_extraccion: str | None = None):
        self.norma = norma
        self.reg = reg
        self.etq = norma.etiqueta_nota
        self.slug_etq = slug(self.etq)
        self.fecha = fecha_extraccion or _dt.date.today().isoformat()
        opciones = reg.opciones(norma.id_fuente, norma.sigla)
        self.estado_norma = opciones.get("estado")
        self.alias_siglas = [str(x) for x in opciones.get("alias_siglas") or []]
        # Fuentes que marcan los apartes tachados explícitamente (Senado):
        # no se infiere el tachado a partir de las notas.
        self.tachado_explicito = opciones.get("fuente") == "senado"
        if norma.url_fuente and norma.url_fuente.startswith("http"):
            self.url = norma.url_fuente
        elif norma.id_fuente:
            self.url = url_para_id(norma.id_fuente)
        else:
            self.url = None
        self.nombres: set[str] = set()
        self.avisos: list[str] = list(norma.avisos)

    # -- nombres únicos
    def _unico(self, nombre: str) -> str:
        base, k = nombre, 2
        while nombre.lower() in self.nombres:
            nombre = f"{base} ({k})"
            k += 1
        self.nombres.add(nombre.lower())
        return nombre

    def _nombre_articulo(self, a: Articulo) -> str:
        nombre = f"art. {a.numero} {self.slug_etq}"
        unico = self._unico(nombre)
        if unico != nombre:
            self.avisos.append(f"artículo repetido: {a.numero} → {unico}")
        return unico

    # -- preparación del árbol
    def _preparar(self, nodo: Nodo, carpeta: Path) -> None:
        nodo.carpeta = carpeta
        sub = [h for h in nodo.hijos if isinstance(h, Nodo)]
        ancho = len(str(len(sub)))
        for k, h in enumerate(sub, start=1):
            nombre = slug(f"{k:0{ancho}d}. {_titulo_nivel(h.nivel)}")
            # h.ancestros incluye a h: «CGP - Libro Primero - Sección Primera - Título I»
            h.nota = self._unico(slug(
                f"{self.slug_etq} - " + " - ".join(_etq_corta(a.nivel) for a in h.ancestros),
                limite=150))
            self._preparar(h, carpeta / nombre)

    # -- render principal
    def escribir(self, destino: Path) -> dict:
        arbol = _arbol(self.norma)
        self.nombres.add(self.slug_etq.lower())
        self._preparar(arbol, destino)
        arts: list[tuple[Articulo, Nodo]] = []

        def recorrer(n: Nodo) -> None:
            for h in n.hijos:
                if isinstance(h, Articulo):
                    arts.append((h, n))
                else:
                    recorrer(h)

        recorrer(arbol)
        nombres_art = {id(a): self._nombre_articulo(a) for a, _ in arts}
        self.nombres_art = nombres_art

        n_notas = 0
        for k, (a, nodo) in enumerate(arts):
            ant = nombres_art[id(arts[k - 1][0])] if k > 0 else None
            sig = nombres_art[id(arts[k + 1][0])] if k + 1 < len(arts) else None
            nodo.carpeta.mkdir(parents=True, exist_ok=True)  # type: ignore[union-attr]
            (nodo.carpeta / f"{nombres_art[id(a)]}.md").write_text(  # type: ignore[operator]
                self._articulo(a, nodo, ant, sig), encoding="utf-8")
            n_notas += 1

        def indices(n: Nodo, hermanos: list[Nodo]) -> None:
            nonlocal n_notas
            sub = [h for h in n.hijos if isinstance(h, Nodo)]
            for k, h in enumerate(sub):
                h.carpeta.mkdir(parents=True, exist_ok=True)  # type: ignore[union-attr]
                ant = sub[k - 1] if k > 0 else None
                sig = sub[k + 1] if k + 1 < len(sub) else None
                (h.carpeta / f"{h.nota}.md").write_text(  # type: ignore[operator]
                    self._indice(h, ant, sig), encoding="utf-8")
                n_notas += 1
                indices(h, sub)

        self.titulos_nivel: dict[str, int] = {}
        for nv in self.norma.niveles:
            k = f"{self.etq} {_titulo_nivel(nv)}".lower()
            self.titulos_nivel[k] = self.titulos_nivel.get(k, 0) + 1
        indices(arbol, [])
        destino.mkdir(parents=True, exist_ok=True)
        (destino / f"{self.slug_etq}.md").write_text(self._raiz(arbol, len(arts)), encoding="utf-8")
        n_notas += 1
        return {"articulos": len(arts), "niveles": len(self.norma.niveles), "notas": n_notas,
                "avisos": self.avisos}

    # -- enlaces auxiliares
    def _link_nodo(self, n: Nodo | None, texto: str | None = None) -> str:
        if n is None or n.nivel is None:
            return f"[[{self.slug_etq}|{texto or self.etq}]]"
        return f"[[{n.nota}|{texto or _etq_corta(n.nivel)}]]"

    def _migas(self, nodo: Nodo) -> str:
        partes = [f"[[{self.slug_etq}|{self.etq}]]"] + [self._link_nodo(a) for a in nodo.ancestros]
        return " › ".join(partes)

    def _aliases_articulo(self, num: str) -> list[str]:
        n = self.norma
        formas_norma = [self.etq, n.nombre_canonico]
        norm = nombre_normalizado(n.tipo, n.numero, n.anio)
        if norm:
            formas_norma.append(norm)
        out: list[str] = []
        for f in dict.fromkeys(formas_norma):
            out += [f"art. {num} {f}", f"{f} art. {num}"]
        if n.sigla:
            out.append(f"{n.sigla} {num}")
        mletra = re.fullmatch(r"(\d+)([A-Z])", num)
        if mletra:  # «410A» también se cita como «410-A» y «410 A»
            for variante in (f"{mletra.group(1)}-{mletra.group(2)}", f"{mletra.group(1)} {mletra.group(2)}"):
                for f in dict.fromkeys(formas_norma):
                    out.append(f"art. {variante} {f}")
        for s in self.alias_siglas:
            out += [f"art. {num} {s}", f"{s} art. {num}", f"{s} {num}"]
        archivo = f"art. {num} {self.slug_etq}"
        return [x for x in dict.fromkeys(out) if x != archivo]

    # -- cuerpo de un artículo
    def _cuerpo(self, a: Articulo) -> tuple[str, int, list[str], list[str]]:
        partes: list[str] = []
        tachados = 0
        modif: list[str] = []
        derog: list[str] = []
        etq_ctx = self.etq
        siguiente_ctx = None
        articulo_completo = any(RE_ART_COMPLETO.search(b.texto) for b in a.bloques + a.notas_cabecera
                                if b.tipo == "nota")
        for b in a.notas_cabecera:
            nota = _render_nota(b, self.etq, self.reg)
            partes.append(nota)
            (derog if b.clase_nota == "warning" else modif if b.clase_nota == "info" else []).extend(_enlaces_en(nota))
        bloques = a.bloques
        for i, b in enumerate(bloques):
            if siguiente_ctx:
                etq_ctx, siguiente_ctx = siguiente_ctx, None
            if b.tipo == "nota":
                nota = _render_nota(b, self.etq, self.reg)
                partes.append(nota)
                (derog if b.clase_nota == "warning" else modif if b.clase_nota == "info" else []).extend(_enlaces_en(nota))
                continue
            if b.tipo == "tabla":
                partes.append(b.texto)
                continue
            texto, objetivo = enlazar_bloque(b.texto, etq_ctx, self.reg)
            if objetivo:
                siguiente_ctx = objetivo
            sig = bloques[i + 1] if i + 1 < len(bloques) else None
            if self.tachado_explicito:
                tachados += "~~" in texto
            elif (sig is not None and sig.tipo == "nota" and sig.clase_nota == "warning"
                    and not RE_ART_COMPLETO.search(sig.texto)) or articulo_completo:
                texto = f"~~{texto}~~"
                tachados += 1
            if b.tipo == "numeral":
                partes.append(f"{b.marca}\\. {texto}")
            elif b.tipo == "literal":
                partes.append(f"{b.marca}) {texto}")
            elif b.tipo == "paragrafo":
                partes.append(_render_paragrafo(texto))
            elif re.match(r"ART[ÍI]CULO\s+TRANSITORIO\.?", texto, re.I):
                partes.append(re.sub(r"^(ART[ÍI]CULO\s+TRANSITORIO\.?)", r"**Artículo transitorio.**",
                                     texto, flags=re.I))
            else:
                partes.append(texto)
        return "\n\n".join(partes), tachados, list(dict.fromkeys(modif)), list(dict.fromkeys(derog))

    def _articulo(self, a: Articulo, nodo: Nodo, ant: str | None, sig: str | None) -> str:
        cuerpo, tachados, modif, derog = self._cuerpo(a)
        vig = _vigencia(a, tachados, self.estado_norma)
        n = self.norma
        fm = ["---", "aliases:"] + [f"  - {_q(x)}" for x in self._aliases_articulo(a.numero)]
        fm += ["tipo: articulo", f"norma: {_q(n.nombre_canonico)}"]
        if n.sigla:
            fm.append(f"sigla: {_q(n.sigla)}")
        fm.append(f"articulo: {_q(a.numero)}")
        if a.epigrafe:
            fm.append(f"epigrafe: {_q(a.epigrafe)}")
        for anc in nodo.ancestros:
            fm.append(f"{_CLAVE_FM[anc.nivel.tipo]}: {_q(self._link_nodo(anc, _titulo_nivel(anc.nivel)))}")
        fm.append(f"vigencia: {_q(vig)}")
        if modif:
            fm += ["modificado_por:"] + [f"  - {_q(x)}" for x in modif]
        if derog:
            fm += ["derogado_por:"] + [f"  - {_q(x)}" for x in derog]
        if ant:
            fm.append(f"anterior: {_q(f'[[{ant}]]')}")
        if sig:
            fm.append(f"siguiente: {_q(f'[[{sig}]]')}")
        if self.url:
            ancla = "" if a.es_transitorio or "funcionpublica" not in self.url else f"#{a.numero}"
            fm.append(f"fuente: {_q(self.url + ancla)}")
        if n.actualizacion_fuente:
            fm.append(f"actualizacion_fuente: {_q(n.actualizacion_fuente)}")
        fm.append(f"fecha_extraccion: {self.fecha}")
        fm += ["tags:", "  - normas/articulo", f"  - normas/{_tag(self.etq)}", f"  - vigencia/{_tag(vig)}"]
        fm.append("---")
        num_vis = a.numero[0].upper() + a.numero[1:] if a.es_transitorio else a.numero
        titulo = f"Artículo {num_vis}" + (f". {a.epigrafe}" if a.epigrafe else "")
        nav = " · ".join(x for x in (
            f"← [[{ant}]]" if ant else "",
            f"↑ {self._link_nodo(nodo if nodo.nivel else None)}",
            f"[[{sig}]] →" if sig else "",
        ) if x)
        aviso = ""
        if self.estado_norma == "derogada":
            aviso = f"> [!warning] Norma derogada: {n.nombre_largo or n.nombre_canonico}\n\n"
        return (f"{chr(10).join(fm)}\n\n{self._migas(nodo)}\n\n## {titulo}\n\n{aviso}"
                f"{cuerpo or '*(Sin texto en la fuente.)*'}\n\n---\n{nav}\n")

    # -- notas índice
    def _rango(self, nodo: Nodo) -> str:
        arts = nodo.articulos()
        if not arts:
            return ""
        if len(arts) == 1:
            return f"art. {arts[0].numero}"
        return f"arts. {arts[0].numero} a {arts[-1].numero}"

    def _indice(self, nodo: Nodo, ant: Nodo | None, sig: Nodo | None) -> str:
        nv = nodo.nivel
        assert nv is not None
        alias_desc = f"{self.etq} {_titulo_nivel(nv)}"
        fm = ["---"]
        if self.titulos_nivel.get(alias_desc.lower(), 0) == 1:
            fm += ["aliases:", f"  - {_q(alias_desc)}"]
        fm += ["tipo: indice", f"norma: {_q(self.norma.nombre_canonico)}"]
        if self.norma.sigla:
            fm.append(f"sigla: {_q(self.norma.sigla)}")
        fm += [f"nivel: {_q(nv.tipo)}", f"etiqueta: {_q(nv.etiqueta)}", f"nombre: {_q(nv.nombre)}"]
        for anc in nodo.ancestros[:-1]:
            fm.append(f"{_CLAVE_FM[anc.nivel.tipo]}: {_q(self._link_nodo(anc, _titulo_nivel(anc.nivel)))}")
        rango = self._rango(nodo)
        if rango:
            fm.append(f"articulos: {_q(rango)}")
        fm += ["tags:", "  - normas/indice", f"  - normas/{_tag(self.etq)}", "---"]
        cuerpo = [f"{self._migas(nodo.padre) if nodo.padre and nodo.padre.nivel else f'[[{self.slug_etq}|{self.etq}]]'}",
                  f"## {_titulo_nivel(nv)}"]
        if rango:
            cuerpo.append(f"*{rango[0].upper() + rango[1:]}*")
        for b in nv.notas:
            cuerpo.append(_render_nota(b, self.etq, self.reg))
        lista = []
        for h in nodo.hijos:
            if isinstance(h, Nodo):
                r = self._rango(h)
                lista.append(f"- {self._link_nodo(h, _titulo_nivel(h.nivel))}" + (f" ({r})" if r else ""))
            else:
                epi = f" — {h.epigrafe}" if h.epigrafe else ""
                lista.append(f"- [[{self.nombres_art[id(h)]}|Artículo {h.numero}]]{epi}")
        cuerpo.append("### Contenido\n\n" + "\n".join(lista))
        nav = " · ".join(x for x in (
            f"← {self._link_nodo(ant)}" if ant else "",
            f"↑ {self._link_nodo(nodo.padre)}",
            f"{self._link_nodo(sig)} →" if sig else "",
        ) if x)
        return "\n".join(fm) + "\n\n" + "\n\n".join(cuerpo) + f"\n\n---\n{nav}\n"

    # -- nota raíz
    def _toc(self, nodo: Nodo, nivel: int = 0) -> list[str]:
        out = []
        for h in nodo.hijos:
            if isinstance(h, Nodo):
                r = self._rango(h)
                out.append("  " * nivel + f"- {self._link_nodo(h, _titulo_nivel(h.nivel))}" + (f" ({r})" if r else ""))
                out += self._toc(h, nivel + 1)
            elif nodo.nivel is None:
                epi = f" — {h.epigrafe}" if h.epigrafe else ""
                out.append("  " * nivel + f"- [[{self.nombres_art[id(h)]}|Artículo {h.numero}]]{epi}")
        return out

    def _raiz(self, arbol: Nodo, n_arts: int) -> str:
        n = self.norma
        titulo = n.nombre_largo or n.titulo or n.nombre_canonico
        aliases = [n.nombre_canonico, nombre_normalizado(n.tipo, n.numero, n.anio), n.nombre_largo,
                   f"art. INTRO {self.etq}", *self.alias_siglas]
        aliases = [a for a in dict.fromkeys(x for x in aliases if x) if a != self.slug_etq]
        fm = ["---", "aliases:"] + [f"  - {_q(a)}" for a in aliases]
        fm += ["tipo: norma", f"norma: {_q(n.nombre_canonico)}"]
        if n.sigla:
            fm.append(f"sigla: {_q(n.sigla)}")
        if n.nombre_largo:
            fm.append(f"nombre: {_q(n.nombre_largo)}")
        for k, v in (("tipo_norma", n.tipo), ("numero", n.numero), ("anio", n.anio), ("fecha", n.fecha),
                     ("epigrafe", n.epigrafe_norma), ("estado", self.estado_norma),
                     ("fuente", self.url), ("actualizacion_fuente", n.actualizacion_fuente)):
            if v:
                fm.append(f"{k}: {_q(v)}")
        fm += [f"fecha_extraccion: {self.fecha}", f"articulos: {n_arts}",
               "tags:", "  - normas/norma", f"  - normas/{_tag(self.etq)}", "---"]
        cuerpo = [f"# {titulo}"]
        datos = [f"**{n.nombre_canonico}**" + (f" ({n.fecha})" if n.fecha else "")]
        if n.epigrafe_norma:
            datos.append(f"*{n.epigrafe_norma}*")
        cuerpo.append("\n\n".join(datos))
        if self.estado_norma == "derogada":
            cuerpo.append("> [!warning] Norma derogada.")
        meta = []
        if self.url:
            origen = ("Secretaría General del Senado" if "secretariasenado" in self.url
                      else "Gestor Normativo de Función Pública")
            meta.append(f"- Fuente: [{origen}]({self.url})")
        if n.actualizacion_fuente:
            meta.append(f"- Actualización de la fuente: {n.actualizacion_fuente}")
        meta.append(f"- Extraído el {self.fecha} · {n_arts} artículos")
        cuerpo.append("\n".join(meta))
        toc = self._toc(arbol)
        if toc:
            cuerpo.append("## Contenido\n\n" + "\n".join(toc))
        if n.preambulo:
            pre = []
            for b in n.preambulo:
                pre.append(_render_nota(b, self.etq, self.reg) if b.tipo == "nota"
                           else b.texto if b.tipo == "tabla" else enlazar(b.texto, self.etq, self.reg))
            cuerpo.append("## Encabezado y preámbulo\n\n" + "\n\n".join(pre))
        if n.envoltura:
            env = [f"Disposiciones de la norma que expide {('el ' + n.nombre_largo) if n.nombre_largo else 'el texto'}:"]
            for a in n.envoltura:
                txt, *_ = self._cuerpo(a)
                env.append(f"### Artículo {a.numero}" + (f". {a.epigrafe}" if a.epigrafe else "") + f"\n\n{txt}")
            cuerpo.append("## Norma que lo expide\n\n" + "\n\n".join(env))
        if n.firmas:
            cuerpo.append("## Firmas\n\n" + "  \n".join(n.firmas))
        if self.avisos:
            av = "\n".join(f"> - {a}" for a in self.avisos[:200])
            cuerpo.append(f"> [!bug]- Avisos de la conversión ({len(self.avisos)})\n{av}")
        return "\n".join(fm) + "\n\n" + "\n\n".join(cuerpo) + "\n"


def render(norma: Norma, destino: str | Path, reg: Registry, *,
           fecha_extraccion: str | None = None, forzar: bool = False) -> dict:
    """Escribe la norma bajo ``destino/<etiqueta>/`` reemplazando la versión previa.

    Devuelve estadísticas: ``raiz``, ``articulos``, ``niveles``, ``notas``, ``avisos``.
    """
    destino = Path(destino)
    r = Renderizador(norma, reg, fecha_extraccion=fecha_extraccion)
    raiz = destino / r.slug_etq
    if raiz.exists() and not forzar:
        propia = (raiz / f"{r.slug_etq}.md").exists() or any(raiz.glob("art. INTRO *.md")) \
            or not any(raiz.iterdir())
        if not propia:
            raise FileExistsError(
                f"{raiz} existe y no parece generada por normas-cli; usa --forzar para reemplazarla")
    destino.mkdir(parents=True, exist_ok=True)
    tmp = destino / f".{r.slug_etq}.tmp-{os.getpid()}"
    if tmp.exists():
        shutil.rmtree(tmp)
    try:
        stats = r.escribir(tmp)
        if raiz.exists():
            shutil.rmtree(raiz)
        tmp.rename(raiz)
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)
    stats["raiz"] = str(raiz)
    return stats
