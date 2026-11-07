"""Modelo de datos de una norma colombiana.

El parser produce una :class:`Norma` que contiene una lista ordenada de
"items": cada item es un :class:`Nivel` (encabezado de jerarquía: LIBRO,
TÍTULO, CAPÍTULO…) o un :class:`Articulo`. El renderizador recorre esa lista
manteniendo una pila de niveles para ubicar cada artículo en su carpeta.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

# Tipos de bloque dentro del cuerpo de un artículo.
TipoBloque = Literal["inciso", "numeral", "literal", "paragrafo", "nota"]

# Jerarquía soportada, de mayor a menor. El índice define la profundidad.
NIVELES = ["PARTE", "LIBRO", "TÍTULO", "SECCIÓN", "CAPÍTULO"]


@dataclass
class HrefRef:
    """Referencia cruzada explícita hallada en un ``<a href>`` de la fuente.

    ``i`` es el id interno de Función Pública (``norma.php?i=<i>``) y ``art`` el
    número de artículo del ancla (``#<art>``). Es la vía más confiable para
    resolver enlaces entre normas.
    """

    i: Optional[str]
    art: Optional[str]
    texto: str


@dataclass
class Bloque:
    """Un párrafo del cuerpo de un artículo, ya clasificado."""

    tipo: TipoBloque
    texto: str
    # Marca de lista para numerales/literales (p. ej. "1." o "a)").
    marca: Optional[str] = None
    # Referencias cruzadas explícitas (de <a href>) contenidas en el bloque.
    hrefs: list[HrefRef] = field(default_factory=list)
    # Para notas editoriales: subtipo de callout (derogado/exequible/…).
    clase_nota: Optional[str] = None


@dataclass
class Articulo:
    numero: str  # "1", "28", "30A", "590-1"…
    epigrafe: Optional[str]
    bloques: list[Bloque] = field(default_factory=list)


@dataclass
class Nivel:
    tipo: str  # uno de NIVELES
    etiqueta: str  # "PRIMERO", "I", "ÚNICO", "PRELIMINAR"…
    nombre: str  # nombre descriptivo (puede ser "")

    @property
    def profundidad(self) -> int:
        return NIVELES.index(self.tipo) if self.tipo in NIVELES else len(NIVELES)


@dataclass
class Norma:
    # Identidad
    id_fuente: Optional[str] = None  # i=<id> de Función Pública
    tipo: Optional[str] = None  # "Ley", "Decreto", "Resolución", "Código"…
    numero: Optional[str] = None  # "1564"
    anio: Optional[str] = None  # "2012"
    sigla: Optional[str] = None  # "CGP" (opcional)
    titulo: Optional[str] = None  # "Ley 1564 de 2012" (h2.titulo-norma)
    epigrafe_norma: Optional[str] = None  # "Por medio de la cual se expide…"
    fecha: Optional[str] = None  # texto de fecha si está disponible
    url_fuente: Optional[str] = None

    # Contenido
    preambulo: list[Bloque] = field(default_factory=list)  # antes del 1er artículo
    items: list = field(default_factory=list)  # mezcla ordenada de Nivel | Articulo

    @property
    def nombre_canonico(self) -> str:
        """Identificador estable: ``"Ley 1564 de 2012"`` (sin sigla)."""
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
