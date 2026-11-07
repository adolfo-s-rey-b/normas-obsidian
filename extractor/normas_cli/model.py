"""Modelo de datos de una norma colombiana.

El parser produce una :class:`Norma` con una lista ordenada de *items*: cada
item es un :class:`Nivel` (encabezado de jerarquía: LIBRO, TÍTULO, CAPÍTULO…)
o un :class:`Articulo`. La profundidad de cada tipo de nivel **no es fija**:
varía entre normas (en el CGP la SECCIÓN está por encima del TÍTULO; en el
Código de Comercio, por debajo del CAPÍTULO), así que el parser la infiere y la
deja en :attr:`Norma.orden_niveles`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

# Tipos de bloque dentro del cuerpo de un artículo.
TipoBloque = Literal["inciso", "numeral", "literal", "paragrafo", "nota", "tabla"]

# Orden por defecto (el más frecuente), usado cuando el documento no permite
# inferir otro. "RUBRO" es un encabezado sin etiqueta (p. ej. «IMPUESTOS
# DEDUCIBLES.» en el Estatuto Tributario) y siempre va al nivel más profundo.
ORDEN_DEFECTO = ["PARTE", "LIBRO", "TÍTULO", "CAPÍTULO", "SECCIÓN", "RUBRO"]


@dataclass
class HrefRef:
    """Referencia cruzada explícita hallada en un ``<a href>`` de la fuente.

    ``i`` es el id interno de Función Pública (``norma.php?i=<i>``) y ``art`` el
    ancla (``#<art>``), que suele ser el número de artículo.
    """

    i: Optional[str]
    art: Optional[str]
    texto: str


@dataclass
class Bloque:
    """Un párrafo del cuerpo de un artículo, ya clasificado."""

    tipo: TipoBloque
    texto: str
    # Marca de lista para numerales/literales (p. ej. "1" o "a").
    marca: Optional[str] = None
    # Referencias cruzadas explícitas (de <a href>) contenidas en el bloque.
    hrefs: list[HrefRef] = field(default_factory=list)
    # Para notas editoriales: subtipo de callout (warning/info/note).
    clase_nota: Optional[str] = None


@dataclass
class Articulo:
    numero: str  # "1", "28", "30A", "590-1", "transitorio 1", "transitorio 1 (AL 1 de 2017)"
    epigrafe: Optional[str]
    bloques: list[Bloque] = field(default_factory=list)
    # Notas editoriales halladas en la propia cabecera (p. ej. «(Adicionado por…)»).
    notas_cabecera: list[Bloque] = field(default_factory=list)

    @property
    def es_transitorio(self) -> bool:
        return self.numero.startswith("transitorio")


@dataclass
class Nivel:
    tipo: str  # PARTE, LIBRO, TÍTULO, SECCIÓN, CAPÍTULO o RUBRO
    etiqueta: str  # "PRIMERO", "I", "ÚNICO", "PRELIMINAR", "3A"…
    nombre: str  # nombre descriptivo (puede ser "")
    # Profundidad asignada por el parser (0 = más alto).
    profundidad: int = 0
    # Notas editoriales sobre el propio nivel («Capítulo adicionado por…»).
    notas: list[Bloque] = field(default_factory=list)

    @property
    def es_preliminar(self) -> bool:
        return self.etiqueta.upper().startswith("PRELIMINAR")


@dataclass
class Norma:
    # Identidad
    id_fuente: Optional[str] = None  # i=<id> de Función Pública
    tipo: Optional[str] = None  # "Ley", "Decreto", "Decreto Ley", "Constitución Política"…
    numero: Optional[str] = None  # "1564"
    anio: Optional[str] = None  # "2012"
    sigla: Optional[str] = None  # "CGP" (opcional)
    nombre_largo: Optional[str] = None  # "Código General del Proceso" (del registry)
    titulo: Optional[str] = None  # "Ley 1564 de 2012" (h2.titulo-norma)
    epigrafe_norma: Optional[str] = None  # "Por medio de la cual se expide…"
    fecha: Optional[str] = None  # "Julio 12"
    actualizacion_fuente: Optional[str] = None  # "27 de agosto de 2025" (DAFP)
    url_fuente: Optional[str] = None

    # Contenido
    preambulo: list[Bloque] = field(default_factory=list)  # antes del 1er artículo
    items: list = field(default_factory=list)  # mezcla ordenada de Nivel | Articulo
    # Artículos de la norma «envoltura» (p. ej. el Decreto 624 de 1989 que
    # expide el Estatuto Tributario): no colisionan con los del estatuto.
    envoltura: list[Articulo] = field(default_factory=list)
    firmas: list[str] = field(default_factory=list)
    orden_niveles: list[str] = field(default_factory=lambda: list(ORDEN_DEFECTO))
    avisos: list[str] = field(default_factory=list)  # problemas detectados al parsear

    @property
    def nombre_canonico(self) -> str:
        """Identificador estable: ``"Ley 1564 de 2012"`` (sin sigla)."""
        if self.tipo and self.tipo.lower().startswith("constituci") and self.anio:
            return f"Constitución Política de {self.anio}"
        if self.tipo and self.numero and self.anio:
            return f"{self.tipo} {self.numero} de {self.anio}"
        return self.titulo or (self.id_fuente or "norma")

    @property
    def etiqueta_nota(self) -> str:
        """Sigla si existe; si no, el nombre canónico (notación de archivos)."""
        return self.sigla or self.nombre_canonico

    @property
    def articulos(self) -> list[Articulo]:
        return [it for it in self.items if isinstance(it, Articulo)]

    @property
    def niveles(self) -> list[Nivel]:
        return [it for it in self.items if isinstance(it, Nivel)]
