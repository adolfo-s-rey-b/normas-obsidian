"""Registro central de normas y siglas (carga/consulta/actualización)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .model import Norma

CABECERA_YAML = """\
# Registro central de normas de la biblioteca (ver README, sección «registry»).
# Lo actualiza `normas-cli`; puede editarse a mano (siglas, nombres, esquema).
"""


def _norm(s: str) -> str:
    s = "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )
    return " ".join(s.lower().split())


def familia_tipo(tipo: str | None) -> str:
    """«Decreto Ley», «Decreto Nacional», «Decreto Legislativo» → «Decreto»."""
    t = _norm(tipo or "")
    if t.startswith("decreto"):
        return "Decreto"
    if t.startswith("resoluci"):
        return "Resolución"
    if t.startswith("acto legislativo"):
        return "Acto Legislativo"
    if t.startswith("constituci"):
        return "Constitución Política"
    return (tipo or "").strip().title()


def nombre_normalizado(tipo: str | None, numero: str | None, anio: str | None) -> str | None:
    """Forma usada en wikilinks a normas no registradas: «Decreto 2651 de 1991»."""
    if not (tipo and numero and anio):
        return None
    fam = familia_tipo(tipo)
    if fam == "Constitución Política":
        return f"Constitución Política de {anio}"
    return f"{fam} {int(numero) if numero.isdigit() else numero} de {anio}"


RE_IDENTIDAD = re.compile(
    r"(Ley|Decreto(?:\s+(?:Ley|Legislativo|Nacional|Reglamentario|Extraordinario))?|"
    r"Resoluci[oó]n|Acuerdo|Acto\s+Legislativo)\s+(?:No\.?\s*|N[°º]\s*)?"
    r"(\d+[A-Za-z]?)\s+de\s+(\d{4})",
    re.I,
)

_CAMPOS = ("id", "tipo", "numero", "anio", "sigla", "nombre", "ruta", "estado")


@dataclass
class EntradaNorma:
    id: str | None = None
    tipo: str | None = None
    numero: str | None = None
    anio: str | None = None
    sigla: str | None = None
    nombre: str | None = None
    ruta: str | None = None
    estado: str | None = None
    extra: dict = field(default_factory=dict)  # jerarquia, esquema…

    @property
    def nombre_canonico(self) -> str:
        if familia_tipo(self.tipo) == "Constitución Política" and self.anio:
            return f"Constitución Política de {self.anio}"
        if self.tipo and self.numero and self.anio:
            return f"{self.tipo} {self.numero} de {self.anio}"
        return self.sigla or (self.id or "norma")

    @property
    def etiqueta(self) -> str:
        """Sigla si existe; si no, el nombre canónico."""
        return self.sigla or self.nombre_canonico

    def a_dict(self) -> dict:
        d = {k: getattr(self, k) for k in _CAMPOS}
        d.update(self.extra)
        return d


@dataclass
class Registry:
    ruta_archivo: Path | None = None
    normas: list[EntradaNorma] = field(default_factory=list)
    codigos: dict[str, str] = field(default_factory=dict)
    _cambios: bool = False

    # --- carga / guardado ---------------------------------------------------
    @classmethod
    def cargar(cls, ruta: str | Path) -> "Registry":
        ruta = Path(ruta)
        if not ruta.exists():
            # Registry vacío auto-creable (uso 100% local sin el repo central).
            return cls(ruta_archivo=ruta)
        data = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
        normas = []
        for n in data.get("normas") or []:
            base = {k: (str(n[k]) if n.get(k) is not None and k in ("id", "numero", "anio") else n.get(k))
                    for k in _CAMPOS}
            extra = {k: v for k, v in n.items() if k not in _CAMPOS}
            normas.append(EntradaNorma(**base, extra=extra))
        codigos = {_norm(k): v for k, v in (data.get("codigos") or {}).items()}
        return cls(ruta_archivo=ruta, normas=normas, codigos=codigos)

    def guardar(self, *, forzar: bool = False) -> bool:
        """Escribe el YAML solo si hubo cambios. Devuelve si escribió."""
        if not self.ruta_archivo or not (self._cambios or forzar):
            return False
        data = {"normas": [n.a_dict() for n in self.normas], "codigos": self.codigos}
        cuerpo = yaml.safe_dump(data, allow_unicode=True, sort_keys=False,
                                default_flow_style=None, width=200)
        self.ruta_archivo.write_text(CABECERA_YAML + cuerpo, encoding="utf-8")
        self._cambios = False
        return True

    # --- consultas ----------------------------------------------------------
    def por_id(self, i: str | None) -> EntradaNorma | None:
        if not i:
            return None
        return next((n for n in self.normas if n.id == str(i)), None)

    def por_identidad(self, tipo: str | None, numero: str | None, anio: str | None) -> EntradaNorma | None:
        if not (tipo and numero and anio):
            return None
        fam = familia_tipo(tipo)
        num = str(int(numero)) if str(numero).isdigit() else str(numero)
        return next(
            (n for n in self.normas
             if n.anio == str(anio) and n.numero is not None
             and (str(int(n.numero)) if n.numero.isdigit() else n.numero) == num
             and familia_tipo(n.tipo) == fam),
            None,
        )

    def por_sigla(self, sigla: str) -> EntradaNorma | None:
        return next((n for n in self.normas if n.sigla == sigla), None)

    def opciones(self, i: str | None, sigla: str | None = None) -> dict:
        """Opciones de parseo de una norma registrada (nombre, jerarquia, esquema)."""
        ent = self.por_id(i) or (self.por_sigla(sigla) if sigla else None)
        if not ent:
            return {}
        return {"nombre": ent.nombre, "estado": ent.estado, **ent.extra}

    def sigla_de_codigo(self, nombre: str) -> str | None:
        return self.codigos.get(_norm(nombre))

    def nombres_de_codigos(self) -> list[str]:
        """Nombres de códigos normalizados, del más largo al más corto."""
        return sorted(self.codigos, key=len, reverse=True)

    def etiqueta_por_identidad(self, tipo: str, numero: str, anio: str) -> str:
        ent = self.por_identidad(tipo, numero, anio)
        if ent:
            return ent.etiqueta
        return nombre_normalizado(tipo, numero, anio) or f"{tipo} {numero} de {anio}"

    def etiqueta_por_id(self, i: str | None, texto_ancla: str | None = None) -> str | None:
        """Etiqueta de wikilink para un id de Función Pública.

        Si el id no está registrado, intenta deducirla del texto del ancla
        (p. ej. «Ley 1996 de 2019»).
        """
        ent = self.por_id(i)
        if ent:
            return ent.etiqueta
        if texto_ancla:
            m = RE_IDENTIDAD.search(texto_ancla)
            if m:
                return self.etiqueta_por_identidad(m.group(1), m.group(2), m.group(3))
        return None

    # --- actualización ------------------------------------------------------
    def registrar(self, norma: Norma, ruta: str | None = None) -> EntradaNorma:
        ent = self.por_id(norma.id_fuente) or self.por_identidad(norma.tipo, norma.numero, norma.anio)
        if not ent:
            ent = EntradaNorma()
            self.normas.append(ent)
            self._cambios = True
        antes = ent.a_dict()
        ent.id = norma.id_fuente or ent.id
        ent.tipo = norma.tipo or ent.tipo
        ent.numero = norma.numero or ent.numero
        ent.anio = norma.anio or ent.anio
        ent.sigla = norma.sigla or ent.sigla
        ent.nombre = ent.nombre or norma.nombre_largo
        ent.ruta = ruta or ent.ruta
        if ent.a_dict() != antes:
            self._cambios = True
        return ent
