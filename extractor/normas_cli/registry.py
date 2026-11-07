"""Registro central de normas y siglas (carga/consulta/actualización)."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .model import Norma


def _norm(s: str) -> str:
    s = "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )
    return " ".join(s.lower().split())


@dataclass
class EntradaNorma:
    id: str | None = None
    tipo: str | None = None
    numero: str | None = None
    anio: str | None = None
    sigla: str | None = None
    ruta: str | None = None

    @property
    def nombre_canonico(self) -> str:
        if self.tipo and self.numero and self.anio:
            return f"{self.tipo} {self.numero} de {self.anio}"
        return self.sigla or (self.id or "norma")

    @property
    def etiqueta(self) -> str:
        """Sigla si existe; si no, el nombre canónico."""
        return self.sigla or self.nombre_canonico


@dataclass
class Registry:
    ruta_archivo: Path | None = None
    normas: list[EntradaNorma] = field(default_factory=list)
    codigos: dict[str, str] = field(default_factory=dict)

    # --- carga / guardado ---------------------------------------------------
    @classmethod
    def cargar(cls, ruta: str | Path) -> "Registry":
        ruta = Path(ruta)
        if not ruta.exists():
            # Registry vacío auto-creable (uso 100% local sin el repo central).
            return cls(ruta_archivo=ruta)
        data = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
        normas = [EntradaNorma(**{k: (str(v) if v is not None and k != "sigla" and k != "ruta" else v)
                                   for k, v in n.items()})
                  for n in (data.get("normas") or [])]
        codigos = {_norm(k): v for k, v in (data.get("codigos") or {}).items()}
        return cls(ruta_archivo=ruta, normas=normas, codigos=codigos)

    def guardar(self) -> None:
        if not self.ruta_archivo:
            return
        data = {
            "normas": [
                {"id": n.id, "tipo": n.tipo, "numero": n.numero, "anio": n.anio,
                 "sigla": n.sigla, "ruta": n.ruta}
                for n in self.normas
            ],
            "codigos": self.codigos,
        }
        self.ruta_archivo.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )

    # --- consultas ----------------------------------------------------------
    def por_id(self, i: str) -> EntradaNorma | None:
        return next((n for n in self.normas if n.id == str(i)), None)

    def por_identidad(self, tipo: str, numero: str, anio: str) -> EntradaNorma | None:
        t = _norm(tipo)
        return next(
            (n for n in self.normas
             if n.numero == str(numero) and n.anio == str(anio)
             and (n.tipo and _norm(n.tipo) == t)),
            None,
        )

    def sigla_de_codigo(self, nombre: str) -> str | None:
        return self.codigos.get(_norm(nombre))

    def etiqueta_por_id(self, i: str, texto_ancla: str | None = None) -> str | None:
        """Etiqueta de wikilink para un id de Función Pública.

        Si el id no está registrado, intenta deducir el nombre del texto del
        ancla (p. ej. "de la Ley 1996 de 2019").
        """
        ent = self.por_id(i)
        if ent:
            return ent.etiqueta
        if texto_ancla:
            import re

            m = re.search(
                r"(Ley|Decreto(?:\s+Ley)?|Resoluci[oó]n|Acuerdo|C[oó]digo)\s+"
                r"(\d+[A-Za-z]?)\s+de\s+(\d{4})",
                texto_ancla,
                re.I,
            )
            if m:
                return f"{m.group(1).title()} {m.group(2)} de {m.group(3)}"
        return None

    # --- actualización ------------------------------------------------------
    def registrar(self, norma: Norma, ruta: str | None = None) -> EntradaNorma:
        ent = (norma.id_fuente and self.por_id(norma.id_fuente)) or (
            norma.tipo and norma.numero and norma.anio
            and self.por_identidad(norma.tipo, norma.numero, norma.anio)
        )
        if not ent:
            ent = EntradaNorma()
            self.normas.append(ent)
        ent.id = norma.id_fuente or ent.id
        ent.tipo = norma.tipo or ent.tipo
        ent.numero = norma.numero or ent.numero
        ent.anio = norma.anio or ent.anio
        ent.sigla = norma.sigla or ent.sigla
        ent.ruta = ruta or ent.ruta
        # Si la norma tiene sigla, la sembramos en el diccionario de códigos.
        if norma.sigla and norma.epigrafe_norma:
            pass
        return ent
