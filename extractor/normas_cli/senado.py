"""Adaptador para la Secretaría General del Senado (Avance Jurídico).

Algunas normas no están en el Gestor Normativo del DAFP (p. ej. el Código
Civil). El Senado las publica en ``basedoc/<norma>.html`` paginadas
(``<norma>_pr001.html``, ``_pr002``…), en ISO-8859-1, con:

* artículos: ``<a class="bookmarkaj" name="33">ARTÍCULO 33. &lt;EPÍGRAFE&gt;.</a> texto``
  (el epígrafe entre ángulos es editorial);
* encabezados: ``<p class="centrado"><a class="bookmarkaj" name="Nivel006">CAPÍTULO V.</a></p>``;
* apartes inexequibles o derogados: ``<S>…</S>``;
* recuadros de vigencia/jurisprudencia/notas del editor rellenados por
  JavaScript (``insRowN()`` en ``js/<página>.js``).

Este módulo descarga todas las páginas y las **normaliza** a la estructura del
DAFP (``h2.titulo-norma`` + ``div.descripcion-contenido``) para reutilizar
``parse()``: los ``<S>`` pasan a ``~~tachado~~`` y los recuadros a notas.
"""

from __future__ import annotations

import html as _html
import re
import time
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .fetch import USER_AGENT, _get

INICIO = "<!--Inicio documento-->"
FIN = "<!--Fin documento-->"
# Recuadros que no se incluyen (texto histórico muy largo).
RECUADROS_OMITIDOS = ("legislación anterior", "legislacion anterior")


def _descargar(url: str, cache: Path | None, *, pausa: float = 0.4) -> str:
    destino = None
    if cache is not None:
        destino = cache / re.sub(r"[^\w.-]+", "_", url.split("//", 1)[-1])
        if destino.exists():
            return destino.read_text(encoding="utf-8")
    resp = _get(url, timeout=90)
    resp.raise_for_status()
    texto = resp.content.decode("cp1252", errors="replace")
    if destino is not None:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
        time.sleep(pausa)  # sin caché: ser amables con el servidor
    return texto


def _recuadros(js: str) -> dict[str, str]:
    """``{"1": "texto plano de insRow1", …}`` a partir del JS de la página."""
    out = {}
    for m in re.finditer(r'function insRow(\d+)\(\)\s*\{\s*var description = new Array\(\);\s*'
                         r'description\[0\] = "(.*?)";\s*var z=', js, re.S):
        contenido = m.group(2).replace('\\"', '"')
        texto = BeautifulSoup(contenido, "html.parser").get_text(" ", strip=True)
        out[m.group(1)] = re.sub(r"\s+", " ", texto).strip()
    return out


def _tachado(m: re.Match) -> str:
    """``<S>texto</S>`` → ``~~texto~~`` como texto plano (sin etiquetas internas,
    que harían que el parser intercale espacios) y con los espacios por fuera."""
    texto = BeautifulSoup(m.group(1), "html.parser").get_text()
    if not texto.strip():
        return texto
    ini = texto[: len(texto) - len(texto.lstrip())]
    fin = texto[len(texto.rstrip()):]
    return f"{ini}~~{_html.escape(texto.strip(), quote=False)}~~{fin}"


def _normalizar_pagina(html: str, recuadros: dict[str, str]) -> str:
    a, b = html.find(INICIO), html.find(FIN)
    cuerpo = html[a + len(INICIO): b if b > 0 else len(html)]
    # Tachados del editor → markdown (antes de que el parser pierda el formato).
    cuerpo = re.sub(r"<S>(.*?)</S>", _tachado, cuerpo, flags=re.S | re.I)
    sopa = BeautifulSoup(cuerpo, "html.parser")
    for nav in sopa.find_all("a", class_="antsig"):
        p = nav.find_parent("p")
        (p or nav).decompose()
    for a_top in sopa.find_all("a", title="Ir al inicio"):
        a_top.decompose()
    for img in sopa.find_all("img"):
        img.decompose()
    # Recuadros: <div><a class="caja_vja_encabezado" href="javascript:insRow7()">Título</a></div><table id="Table7">
    for enc in sopa.find_all("a", class_="caja_vja_encabezado"):
        titulo = enc.get_text(" ", strip=True)
        m = re.search(r"insRow(\d+)", enc.get("href", ""))
        div = enc.find_parent("div") or enc
        tabla = div.find_next_sibling("table")
        texto = recuadros.get(m.group(1), "") if m else ""
        nuevo = None
        if texto and titulo.lower() not in RECUADROS_OMITIDOS:
            nuevo = sopa.new_tag("p")
            nuevo.string = f"({titulo}: {texto.lstrip('- ')})"
        if tabla is not None:
            tabla.decompose()
        if nuevo is not None:
            div.replace_with(nuevo)
        else:
            div.decompose()
    # Encabezados centrados.
    for p in sopa.find_all("p", class_="centrado"):
        p["align"] = "center"
        for x in p.find_all(["a", "span"]):
            x.name = "strong"
            x.attrs = {}
    # Cabeceras de artículo: <a class="bookmarkaj" name="33">ARTÍCULO 33. <EPÍGRAFE>.</a> <marcas>
    for a in sopa.find_all("a", class_="bookmarkaj"):
        if not re.fullmatch(r"\d+[A-Za-z-]*", a.get("name", "")):
            continue
        cab = a.get_text(" ", strip=True)
        cab = re.sub(r"<\s*([^<>]+?)\s*>", r"\1", cab)  # epígrafe editorial sin ángulos
        strong = sopa.new_tag("strong")
        strong.string = cab
        # Marcas editoriales al inicio del texto: «<Apartes tachados INEXEQUIBLES>».
        sig = a.next_sibling
        if isinstance(sig, str):
            marcas = re.findall(r"<\s*([^<>]{3,200}?)\s*>", sig)
            resto = re.sub(r"^\s*(?:<\s*[^<>]{3,200}?\s*>\s*)+", " ", sig)
            utiles = [x for x in marcas if not re.match(r"(?i)ver\b", x)]
            if utiles:
                strong.string = cab + " " + " ".join(f"({x})" for x in utiles)
            sig.replace_with(resto)
        a.replace_with(strong)
    return str(sopa)


def descargar_norma(url_inicial: str, *, cache_dir: str | Path | None = None,
                    titulo: str, actualizacion: str | None = None) -> str:
    """Descarga todas las páginas y devuelve un HTML con la estructura del DAFP."""
    cache = Path(cache_dir) / "senado" if cache_dir else None
    url = url_inicial
    vistas: set[str] = set()
    partes: list[str] = []
    while url and url not in vistas:
        vistas.add(url)
        pagina = _descargar(url, cache)
        if actualizacion is None:
            m = re.search(r"[ÚU]ltima actualizaci[óo]n:\s*([^<(]+)", _html.unescape(pagina))
            if m:
                actualizacion = m.group(1).strip(" -")
        nombre_js = re.sub(r"\.html?$", ".js", url.rsplit("/", 1)[-1])
        js = ""
        try:
            js = _descargar(urljoin(url, f"js/{nombre_js}"), cache)
        except Exception:  # noqa: BLE001 — sin recuadros si el JS no existe
            pass
        partes.append(_normalizar_pagina(pagina, _recuadros(js)))
        m = re.search(r'<a class=antsig href="([^"]+)">Siguiente</a>', pagina)
        url = urljoin(url, m.group(1)) if m else None
    pre = f"<p>ACTUALIZACIÓN: {actualizacion}</p>" if actualizacion else ""
    return (f'<html><head><meta charset="utf-8"></head><body>'
            f'<h2 class="titulo-norma">{titulo}</h2>'
            f'<div class="descripcion-contenido">{pre}{"".join(partes)}</div></body></html>')


__all__ = ["descargar_norma", "USER_AGENT"]
