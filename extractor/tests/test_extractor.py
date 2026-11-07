"""Pruebas del extractor sobre fixtures reales de Función Pública.

Cubren las dos variantes de markup verificadas (CGP con <em>, Ley 1996 con
entidades) y el motor de wikilinks (internos, externos y cruces por href).
"""

from pathlib import Path

import pytest

from normas_cli.links import enlazar
from normas_cli.model import Articulo, Nivel
from normas_cli.parse import parse
from normas_cli.registry import Registry
from normas_cli.render import render

FIXTURES = Path(__file__).parent / "fixtures"
REGISTRY = Path(__file__).parent.parent / "registry.yaml"


def _norma(nombre, idf, sigla=None):
    html = (FIXTURES / nombre).read_text(encoding="utf-8")
    n = parse(html, id_fuente=idf)
    n.sigla = sigla
    return n


@pytest.fixture
def reg():
    return Registry.cargar(REGISTRY)


def test_cgp_identidad_y_conteo():
    n = _norma("cgp_i48425.html", "48425", "CGP")
    assert (n.tipo, n.numero, n.anio) == ("Ley", "1564", "2012")
    assert n.nombre_canonico == "Ley 1564 de 2012"
    assert n.etiqueta_nota == "CGP"
    # El CGP tiene del orden de 627 artículos.
    assert len(n.articulos) > 600
    assert any(isinstance(it, Nivel) and it.tipo == "LIBRO" for it in n.items)


def test_cgp_epigrafe_y_numerales():
    n = _norma("cgp_i48425.html", "48425", "CGP")
    art1 = next(a for a in n.articulos if a.numero == "1")
    assert art1.epigrafe.lower().startswith("objeto")
    art17 = next(a for a in n.articulos if a.numero == "17")
    marcas = [b.marca for b in art17.bloques if b.tipo == "numeral"]
    assert marcas[:3] == ["1", "2", "3"]
    assert any(b.tipo == "paragrafo" for b in art17.bloques)


def test_ley1996_variante_vieja():
    """Markup con entidades, MAYÚSCULAS y epígrafe fuera de <em>."""
    n = _norma("ley1996_i99712.html", "99712")
    assert (n.tipo, n.numero, n.anio) == ("Ley", "1996", "2019")
    assert n.etiqueta_nota == "Ley 1996 de 2019"  # sin sigla → fallback
    art1 = next(a for a in n.articulos if a.numero == "1")
    assert art1.epigrafe.lower().startswith("objeto")
    assert len(n.articulos) > 40


def test_decreto_1991_variante_malformada():
    """Tercera variante: <P> en mayúsculas, atributos sin comillas, HTML roto.

    Documenta la robustez del parser ante páginas viejas malformadas. Por la
    corrupción de etiquetas (</FONT> sueltos) puede perderse algún artículo
    fusionado con el preámbulo, pero debe recuperar la gran mayoría.
    """
    n = _norma("decreto2651_i14319.html", "14319")
    assert n.tipo and n.tipo.startswith("Decreto")
    assert (n.numero, n.anio) == ("2651", "1991")
    assert len(n.articulos) >= 50  # ~62 artículos


def test_enlaces_internos_y_externos(reg):
    # Referencia interna (misma norma) → usa la sigla actual.
    t = enlazar("según el artículo 590 de este código", "CGP", reg)
    assert "[[art. 590 CGP|590]]" in t
    # Referencia externa nombrada → sigla del registro de códigos.
    t = enlazar("los artículos 913 y 914 del Código de Comercio", "CGP", reg)
    assert "[[art. 913 CCo|913]]" in t and "[[art. 914 CCo|914]]" in t
    # Ley externa numerada → identificador canónico.
    t = enlazar("conforme al artículo 35 de la Ley 1996 de 2019", "CGP", reg)
    assert "[[art. 35 Ley 1996 de 2019|35]]" in t
    # El año de la ley NO debe enlazarse.
    assert "[[art. 2019" not in t


def test_render_y_cruce_real(tmp_path, reg):
    """Convierte CGP + Ley 1996 y verifica que el cruce de derogatoria resuelve."""
    cgp = _norma("cgp_i48425.html", "48425", "CGP")
    ley = _norma("ley1996_i99712.html", "99712")
    render(cgp, tmp_path, reg)
    render(ley, tmp_path, reg)

    # El destino del cruce existe con el nombre canónico esperado.
    destinos = list((tmp_path / "Ley 1996 de 2019").rglob("art. 61 Ley 1996 de 2019.md"))
    assert destinos, "no se generó la nota destino del cruce"

    # El art. 22 del CGP contiene el callout con el wikilink a la Ley 1996.
    art22 = next((tmp_path / "CGP").rglob("art. 22 CGP.md"))
    txt = art22.read_text(encoding="utf-8")
    assert "[[art. 61 Ley 1996 de 2019" in txt
    assert "[!warning]" in txt
    # El inciso derogado quedó tachado.
    assert "~~" in txt
    # Frontmatter con alias dual (sigla + identificador).
    assert "art. 22 Ley 1564 de 2012" in txt
