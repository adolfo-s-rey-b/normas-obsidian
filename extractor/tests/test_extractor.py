"""Pruebas del extractor sobre fixtures reales de Función Pública.

Ver ``tests/README.md`` para el inventario de fixtures y qué cubre cada uno.
"""

import json
import re
from collections import Counter
from pathlib import Path

import pytest

from normas_cli.catalogo import generar_catalogo
from normas_cli.fetch import id_desde_url
from normas_cli.links import enlazar, enlazar_bloque
from normas_cli.model import Nivel
from normas_cli.parse import _cabecera, parse
from normas_cli.registry import Registry
from normas_cli.render import render, slug
from normas_cli.verificar import frontmatter, verificar

FIXTURES = Path(__file__).parent / "fixtures"
REGISTRY = Path(__file__).parent.parent / "registry.yaml"


@pytest.fixture(scope="module")
def reg():
    return Registry.cargar(REGISTRY)


def _norma(nombre, idf, reg=None, sigla=None):
    html = (FIXTURES / nombre).read_text(encoding="utf-8")
    opciones = reg.opciones(idf) if reg else {}
    n = parse(html, id_fuente=idf, opciones=opciones)
    if sigla:
        n.sigla = sigla
    return n


@pytest.fixture(scope="module")
def cgp(reg):
    return _norma("cgp_i48425.html", "48425", reg, "CGP")


@pytest.fixture(scope="module")
def ley1996(reg):
    return _norma("ley1996_i99712.html", "99712", reg)


# --- Cabeceras de artículo ----------------------------------------------------


@pytest.mark.parametrize("texto,numero", [
    ("ARTÍCULO 15. Competencia", "15"),
    ("ARTÍCULO 1°. Objeto. La presente ley", "1"),
    ("ARTICULO 1o. OBJETO.", "1"),
    ("ARTÍCULO 397A. ALIMENTOS", "397A"),
    ("ARTÍCULO 115-1. DEDUCCIÓN", "115-1"),
    ("ARTÍCULO 5 EL IMPUESTO SOBRE LA RENTA", "5"),
    ("ARTÍCULO TRANSITORIO 3. Texto", "transitorio 3"),
    ("ARTÍCULO TRANSITORIO. En desarrollo", "transitorio"),
    ("ARTICULOS 438. INICIACION DE LABORES.", "438"),
])
def test_cabecera_valida(texto, numero):
    c = _cabecera(texto)
    assert c is not None and c.numero == numero


@pytest.mark.parametrize("texto", [
    "artículos 7° y 8° de la Ley 25 de 1992",      # plural / minúscula
    "Artículo 5 de la Ley 100 de 1993",             # referencia inline
    "ARTÍCULO 54 inciso 4° de la Ley 270",
    "ARTICULOS 93, 94, 95, 96 y 97",                # enumeración, no cabecera
    "artículo 5.",
])
def test_cabecera_invalida(texto):
    assert _cabecera(texto) is None


# --- CGP ---------------------------------------------------------------------------


def test_cgp_identidad_y_conteo(cgp):
    assert (cgp.tipo, cgp.numero, cgp.anio) == ("Ley", "1564", "2012")
    assert cgp.nombre_canonico == "Ley 1564 de 2012"
    assert cgp.etiqueta_nota == "CGP"
    assert len(cgp.articulos) == 628
    assert cgp.epigrafe_norma.startswith("Por medio de la cual se expide el Código General")
    assert cgp.actualizacion_fuente


def test_cgp_sin_articulos_fantasma(cgp):
    """El art. 626 (derogatorias) enumera «artículos 7° y 8°…»: no son cabeceras."""
    nums = [a.numero for a in cgp.articulos]
    assert not [n for n, k in Counter(nums).items() if k > 1]
    art626 = next(a for a in cgp.articulos if a.numero == "626")
    texto = " ".join(b.texto for b in art626.bloques)
    assert "Ley 1395 de 2010" in texto  # el final de la enumeración sigue en el 626
    assert nums[-1] == "627"


def test_cgp_jerarquia_inferida(cgp):
    assert cgp.orden_niveles[:4] == ["LIBRO", "SECCIÓN", "TÍTULO", "CAPÍTULO"]
    pre = next(n for n in cgp.niveles if n.es_preliminar)
    libro = next(n for n in cgp.niveles if n.tipo == "LIBRO")
    assert pre.profundidad == libro.profundidad  # hermanos, no padre e hijo


def test_cgp_articulo_reformatorio_sin_epigrafe(cgp):
    """La frase «Modifíquese … quedará así:» en negrita no es la rúbrica."""
    a620 = next(a for a in cgp.articulos if a.numero == "620")
    assert a620.epigrafe is None and a620.bloques[0].texto.startswith("Modifíquese el parágrafo")


def test_cgp_epigrafe_numerales_y_firmas(cgp):
    art1 = next(a for a in cgp.articulos if a.numero == "1")
    assert art1.epigrafe.lower().startswith("objeto")
    assert art1.bloques[0].texto.endswith(".")  # conserva el punto final
    art17 = next(a for a in cgp.articulos if a.numero == "17")
    assert [b.marca for b in art17.bloques if b.tipo == "numeral"][:3] == ["1", "2", "3"]
    assert any(b.tipo == "paragrafo" for b in art17.bloques)
    assert cgp.firmas  # el bloque de firmas no queda dentro del art. 627
    art627 = next(a for a in cgp.articulos if a.numero == "627")
    assert not any("PRESIDENTE" in b.texto for b in art627.bloques)


# --- Otras variantes ---------------------------------------------------------------


def test_ley1996_rubrica_en_texto(ley1996):
    assert (ley1996.tipo, ley1996.numero, ley1996.anio) == ("Ley", "1996", "2019")
    assert ley1996.etiqueta_nota == "Ley 1996 de 2019"
    arts = {a.numero: a for a in ley1996.articulos}
    assert arts["1"].epigrafe.lower().startswith("objeto")
    assert arts["37"].epigrafe.startswith("Adjudicación de apoyos")
    # El 62 no tiene rúbrica: su texto completo es cuerpo, no epígrafe.
    assert arts["62"].epigrafe is None and arts["62"].bloques
    assert ley1996.epigrafe_norma.startswith("Por medio de la cual")
    assert len(ley1996.firmas) > 5


def test_decreto_1991_malformado():
    n = _norma("decreto2651_i14319.html", "14319")
    assert n.tipo.startswith("Decreto") and (n.numero, n.anio) == ("2651", "1991")
    assert len(n.articulos) >= 60
    art2 = next(a for a in n.articulos if a.numero == "2")
    assert art2.bloques and art2.bloques[0].texto.startswith("En los procesos")


def test_cn_transitorios_y_esquema(reg):
    n = _norma("cn_i4125_recorte.html", "4125", reg, "CPol")
    assert n.nombre_canonico == "Constitución Política de 1991"
    nums = [a.numero for a in n.articulos]
    assert len(nums) == len(set(nums))
    assert "transitorio 1" in nums and "transitorio 1 (AL 1 de 2017)" in nums
    assert "transitorio 1 (AL 3 de 2017)" in nums and "transitorio (AL 2 de 2017)" in nums
    art1 = n.articulos[0]
    assert art1.epigrafe is None and art1.bloques[0].texto.startswith("Colombia es un Estado social")
    titulos = [(x.tipo, x.etiqueta) for x in n.niveles]
    assert ("TÍTULO", "I") in titulos and ("TÍTULO", "TRANSITORIO") in titulos
    assert n.firmas


def test_et_envoltura():
    n = _norma("et_i6533_recorte.html", "6533")
    assert [a.numero for a in n.envoltura] == ["1", "2", "3", "4"]
    assert [a.numero for a in n.articulos][:3] == ["1", "2", "3"]
    art5 = next(a for a in n.articulos if a.numero == "5")
    assert art5.epigrafe.startswith("EL IMPUESTO SOBRE LA RENTA")


def test_cco_dos_articulos_en_un_parrafo():
    n = _norma("cco_i41102_recorte.html", "41102")
    arts = {a.numero: a for a in n.articulos}
    assert "837" in arts and arts["837"].epigrafe == "EXHIBICIÓN DEL PODER"
    assert arts["1"].epigrafe == "APLICABILIDAD DE LA LEY COMERCIAL"


def test_cst_listas_ol():
    n = _norma("cst_i199983_recorte.html", "199983")
    art77 = next(a for a in n.articulos if a.numero == "77")
    assert art77.bloques and art77.bloques[0].tipo == "numeral"


def test_tablas_y_numeracion_compuesta():
    html = """<h2 class="titulo-norma">Ley 9 de 2020</h2><div class="descripcion-contenido">
    <p><strong>ARTÍCULO 115. TARIFA.</strong> La tarifa es:</p>
    <table><tr><td>Rango</td><td>Tarifa</td></tr><tr><td>0 a 10</td><td>5%</td></tr></table>
    <p><strong>ARTÍCULO 115-1. OTRO.</strong> Texto.</p></div>"""
    n = parse(html)
    a115 = n.articulos[0]
    assert [a.numero for a in n.articulos] == ["115", "115-1"]
    assert a115.bloques[-1].tipo == "tabla" and "| 0 a 10 | 5% |" in a115.bloques[-1].texto


# --- Enlaces --------------------------------------------------------------------------


@pytest.mark.parametrize("texto,actual,esperado,prohibido", [
    ("según el artículo 590 de este código", "CGP", ["[[art. 590 CGP|590]]"], []),
    ("los artículos 913 y 914 del Código de Comercio", "CGP",
     ["[[art. 913 CCo|913]]", "[[art. 914 CCo|914]]"], []),
    ("conforme al artículo 35 de la Ley 1996 de 2019", "CGP", ["[[art. 35 Ley 1996 de 2019|35]]"],
     ["[[art. 2019"]),
    ("normas previstas en el artículo 87, en la Ley 1306 de 2009", "CGP",
     ["[[art. 87 Ley 1306 de 2009|87]]"], ["CGP|1306", "CGP|2009"]),
    ("el artículo 1312 del Código Civil o el compañero permanente", "CGP", ["[[art. 1312 CC|1312]]"], []),
    ("el artículo 432 del Código de Procedimiento Civil ya se", "CGP", ["[[art. 432 CPC|432]]"], []),
    ("el artículo 58 numeral 4 de la Ley 1480 de 2011", "CGP", ["[[art. 58 Ley 1480 de 2011|58]]"],
     ["|4]]"]),
    ("Corregido por el art. 16, Decreto Nacional 1736 de 2012", "CGP",
     ["[[art. 16 Decreto 1736 de 2012|16]]"], []),
    ("artículo 22 de la Ley 1564 de 2012", "Ley 1996 de 2019", ["[[art. 22 CGP|22]]"], []),
    ("el artículo transitorio 5 de la Constitución", "CGP", ["[[art. transitorio 5 CPol|5]]"], []),
    ("del artículo 123 del Código Penitenciario", "CGP", [], ["[["]),
    ("del artículo 1944 del citado código", "CGP", [], ["[["]),
    ("declarado EXEQUIBLE por el artículo 5 en Sentencia C-726 de 2014", "CGP", [], ["|726]]", "|2014]]"]),
    ("el presente artículo, con multa de dos mil (2.000) salarios", "CGP", [], ["[["]),
    ("lo dispuesto en el artículo 771-5 del Estatuto Tributario", "CGP", ["[[art. 771-5 ET|771-5]]"], []),
])
def test_enlaces(reg, texto, actual, esperado, prohibido):
    t = enlazar(texto, actual, reg)
    for e in esperado:
        assert e in t, t
    for p in prohibido:
        assert p not in t, t


@pytest.mark.parametrize("texto,actual,esperado", [
    ("La Ley 599 de 2000 tendrá un artículo 250A, el cual quedará así:", "Ley 1474 de 2011",
     "[[art. 250A CP|250A]]"),
    ("Tráfico de migrantes (C. P. artículo 188), trata", "Ley 1474 de 2011", "[[art. 188 CP|188]]"),
    ("el artículo 20 del C.G.P. y el artículo 5 del C. de Co. Fin.", "CPP", "[[art. 5 CCo|5]]"),
    ("el artículo 20 del C.G.P. y otros", "CPP", "[[art. 20 CGP|20]]"),
])
def test_enlaces_reforma_y_abreviaturas(reg, texto, actual, esperado):
    assert esperado in enlazar(texto, actual, reg)


def test_enlace_texto_citado(reg):
    t, ctx = enlazar_bloque(
        'Modifíquese el numeral 6 del artículo 577 de la Ley 1564 de 2012, así: "Ver artículo 5"',
        "Ley 1996 de 2019", reg)
    assert ctx == "CGP" and "[[art. 5 CGP|5]]" in t


# --- Render, verificación y catálogo ------------------------------------------------------


@pytest.fixture(scope="module")
def biblioteca(tmp_path_factory, reg, cgp, ley1996):
    destino = tmp_path_factory.mktemp("biblioteca")
    render(cgp, destino, reg, fecha_extraccion="2026-01-01")
    render(ley1996, destino, reg, fecha_extraccion="2026-01-01")
    return destino


def test_render_estructura(biblioteca):
    raiz = biblioteca / "CGP"
    assert (raiz / "CGP.md").exists()
    vacias = [d for d in raiz.rglob("*") if d.is_dir() and not any(d.iterdir())]
    assert not vacias
    # SECCIÓN contiene TÍTULO
    art15 = next(raiz.rglob("art. 15 CGP.md"))
    partes = art15.relative_to(raiz).parts
    assert "LIBRO PRIMERO" in partes[0] and "SECCIÓN PRIMERA" in partes[1] and "TÍTULO I" in partes[2]
    assert len(list(raiz.rglob("art. 5 CGP.md"))) == 1


def test_render_frontmatter_y_navegacion(biblioteca):
    art22 = next((biblioteca / "CGP").rglob("art. 22 CGP.md"))
    txt = art22.read_text(encoding="utf-8")
    fm = frontmatter(txt)
    assert "art. 22 Ley 1564 de 2012" in fm["aliases"]
    assert "CGP 22" in fm["aliases"]
    assert fm["vigencia"] == "parcialmente derogado"
    assert "[[art. 61 Ley 1996 de 2019]]" in fm["derogado_por"]
    assert fm["anterior"] == "[[art. 21 CGP]]" and fm["siguiente"] == "[[art. 23 CGP]]"
    assert fm["capitulo"].startswith("[[CGP - Libro Primero - Sección Primera - Título I - Capítulo I|")
    assert fm["fuente"].endswith("norma.php?i=48425#22")
    assert "~~De la designación y remoción" in txt and "[!warning]" in txt
    assert "← [[art. 21 CGP]]" in txt


def test_render_indice_y_raiz(biblioteca):
    indice = next((biblioteca / "CGP").rglob("CGP - Libro Primero - Sección Primera - Título I - Capítulo I.md"))
    txt = indice.read_text(encoding="utf-8")
    assert "[[art. 15 CGP|Artículo 15]]" in txt and frontmatter(txt)["tipo"] == "indice"
    raiz = (biblioteca / "CGP" / "CGP.md").read_text(encoding="utf-8")
    fm = frontmatter(raiz)
    assert fm["tipo"] == "norma" and fm["articulos"] == 628 and "Ley 1564 de 2012" in fm["aliases"]
    assert "## Contenido" in raiz and "## Firmas" in raiz


def test_render_reemplaza_notas_obsoletas(tmp_path, reg, ley1996):
    render(ley1996, tmp_path, reg)
    sobra = tmp_path / "Ley 1996 de 2019" / "art. 999 Ley 1996 de 2019.md"
    sobra.write_text("obsoleta", encoding="utf-8")
    render(ley1996, tmp_path, reg)
    assert not sobra.exists()


def test_render_no_pisa_carpetas_ajenas(tmp_path, reg, ley1996):
    ajena = tmp_path / "Ley 1996 de 2019"
    ajena.mkdir()
    (ajena / "mis notas.md").write_text("x", encoding="utf-8")
    with pytest.raises(FileExistsError):
        render(ley1996, tmp_path, reg)


def test_verificar_y_catalogo(biblioteca, tmp_path):
    lineas: list[str] = []
    assert verificar(biblioteca, salida=lineas.append) == 0, "\n".join(lineas)
    indice = generar_catalogo(biblioteca, tmp_path / "catalogo", imprimir=lambda *_: None)
    assert {n["carpeta"] for n in indice["normas"]} == {"CGP", "Ley 1996 de 2019"}
    cgp = next(n for n in indice["normas"] if n["carpeta"] == "CGP")
    paquete = json.loads((tmp_path / "catalogo" / cgp["paquete"]).read_text(encoding="utf-8"))
    assert paquete["hash"] == cgp["hash"] and "CGP/CGP.md" in paquete["archivos"]
    assert cgp["notas"] == len(paquete["archivos"])


def test_utilidades():
    assert id_desde_url("https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=48425") == "48425"
    largo = slug("TÍTULO V - CONFLICTOS DE COMPETENCIA, IMPEDIMENTOS Y RECUSACIONES, ACUMULACIÓN "
                 "DE PROCESOS, AMPARO DE POBREZA, INTERRUPCIÓN Y SUSPENSIÓN DEL PROCESO")
    assert largo.endswith("…") and len(largo) <= 111
    assert largo[:-1].split()[-1] in ("POBREZA", "AMPARO", "DE", "INTERRUPCIÓN", "PROCESOS")  # palabra completa
    assert isinstance(Nivel("LIBRO", "I", "x").es_preliminar, bool)


# --- Senado y comparación de fuentes ------------------------------------------------


def test_senado_normaliza_pagina():
    from normas_cli.senado import _normalizar_pagina, _recuadros

    pagina = (FIXTURES / "senado_cc_pr001_recorte.html").read_text(encoding="utf-8")
    js_ = (FIXTURES / "senado_cc_pr001_recorte.js").read_text(encoding="utf-8")
    cuerpo = _normalizar_pagina(pagina, _recuadros(js_))
    html = (f'<h2 class="titulo-norma">Ley 84 de 1873</h2>'
            f'<div class="descripcion-contenido">{cuerpo}</div>')
    n = parse(html)
    arts = {a.numero: a for a in n.articulos}
    assert {"33", "34"} <= arts.keys()
    a33 = arts["33"]
    assert a33.epigrafe == "PALABRAS RELACIONADAS CON LAS PERSONAS"
    assert a33.bloques[0].texto.startswith("La~~s~~ palabra~~s~~")  # tachados del editor
    assert not any(re.search(r"(?:^|\s)~~\s", b.texto) for b in a33.bloques)  # apertura sin espacio
    assert any(b.tipo == "nota" and "INEXEQUIBLES" in b.texto for b in a33.bloques + a33.notas_cabecera)
    assert any(nv.tipo == "CAPÍTULO" and nv.etiqueta == "V" for nv in n.niveles)


def test_comparar_fuentes():
    from normas_cli.comparar import comparar, url_senado

    a = parse('<h2 class="titulo-norma">Ley 1 de 2000</h2><div class="descripcion-contenido">'
              "<p><strong>ARTÍCULO 1o.</strong> Texto igual.</p>"
              "<p><strong>ARTÍCULO 2o.</strong> Texto viejo del artículo.</p>"
              "<p><strong>ARTÍCULO 3o.</strong> Solo aquí.</p></div>")
    b = parse('<h2 class="titulo-norma">Ley 1 de 2000</h2><div class="descripcion-contenido">'
              "<p><strong>ARTÍCULO 1.</strong> Texto  igual</p>"
              "<p><strong>ARTÍCULO 2.</strong> Texto nuevo del artículo.</p></div>")
    c = comparar(a, b)
    assert c.identicos == 1 and [d.numero for d in c.diferentes] == ["2"] and c.solo_a == ["3"]
    assert url_senado(None, "Ley", "80", "1993").endswith("ley_0080_1993.html")
    assert url_senado("CCo", None, None, None).endswith("codigo_comercio.html")


# --- Consolidación multifuente y decretos únicos -------------------------------------


def _ley(*arts):
    cuerpo = "".join(f"<p><strong>ARTÍCULO {n}.</strong> {t}</p>" + (f"<p>({nota})</p>" if nota else "")
                     for n, t, nota in arts)
    return parse(f'<h2 class="titulo-norma">Ley 9 de 2000</h2><div class="descripcion-contenido">{cuerpo}</div>')


def test_consolidar_toma_la_version_mas_reciente():
    from normas_cli.consolidar import Fuente, consolidar

    dafp = _ley(("1", "Texto igual.", None),
                ("2", "Texto modificado en 2023.", "Modificado por el Art. 5 de la Ley 2294 de 2023"),
                ("3", "Texto nuevo del DAFP.", "Modificado por el Art. 9 de la Ley 2500 de 2025"))
    senado = _ley(("1", "Texto igual.", None),
                  ("2", "Texto original revivido.",
                   "Jurisprudencia Vigencia: artículo 5 de la Ley 2294 de 2023 declarado INEXEQUIBLE "
                   "mediante Sentencia C-038-25"),
                  ("3", "Texto viejo.", "Modificado por el artículo 1 de la Ley 100 de 1993"),
                  ("3A", "Solo en el Senado.", None))
    n = consolidar([Fuente("DAFP", "https://dafp", dafp), Fuente("Senado", "http://senado", senado, True)])
    arts = {a.numero: a for a in n.articulos}
    assert [a.numero for a in n.articulos] == ["1", "2", "3", "3A"]
    assert arts["1"].coincidencia == "idéntico"
    assert arts["2"].fuente == "Senado" and arts["2"].reforma == 2025  # la sentencia es posterior
    assert arts["3"].fuente == "DAFP" and arts["3"].reforma == 2025
    assert arts["3A"].coincidencia == "solo en Senado"
    c = n.consolidacion
    assert c["base"] == "Senado" and c["identicos"] == 1 and c["diferentes"] == 2


def test_decreto_unico_numeracion_punteada():
    html = ('<h2 class="titulo-norma">Decreto 1082 de 2015</h2><div class="descripcion-contenido">'
            '<p align="center"><strong>SUBSECCIÓN 1</strong></p><p align="center"><strong>Generalidades</strong></p>'
            "<p><strong>ARTÍCULO 2.2.1.1.1.1.1. <em>Objetivos.</em></strong> Las entidades…</p>"
            "<p><strong>ARTÍCULO 2.2.1.1.1.1.2. <em>Definiciones.</em></strong> Para efectos…</p>"
            "<p><strong>ARTÍCULO 2.2.1.1.1.2.1. <em>Plan.</em></strong> Según el artículo 2.2.1.1.1.1.1.</p></div>")
    n = parse(html)
    assert [a.numero for a in n.articulos] == ["2.2.1.1.1.1.1", "2.2.1.1.1.1.2", "2.2.1.1.1.2.1"]
    assert n.niveles[0].tipo == "SUBSECCIÓN"


def test_enlace_decreto_unico(reg):
    t = enlazar("conforme al artículo 2.2.1.2.3.2.3 del Decreto 1082 de 2015 y 2.000.000 pesos", "CGP", reg)
    assert "[[art. 2.2.1.2.3.2.3 Decreto 1082 de 2015|2.2.1.2.3.2.3]]" in t and "|2.000" not in t
