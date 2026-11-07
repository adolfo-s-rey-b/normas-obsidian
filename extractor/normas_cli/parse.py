"""Parser tolerante a variantes del HTML de Función Pública.

Trabaja sobre el *texto decodificado* (BeautifulSoup resuelve entidades como
``&Iacute;`` o ``&#176;``) y clasifica los párrafos por su contenido, no por la
anidación exacta de etiquetas. Así soporta:

  * markup nuevo: ``<p><strong>Artículo 15. <em>Epígrafe</em>.</strong> texto</p>``
  * markup viejo: ``<p><strong>ARTÍCULO 1°. </strong>Objeto. texto</p>`` (entidades)
"""

from __future__ import annotations

import re
import unicodedata

from bs4 import BeautifulSoup, Tag

from .model import Articulo, Bloque, HrefRef, Nivel, Norma

# --- Expresiones regulares principales -------------------------------------

# Cabecera de artículo. Anclada al inicio del párrafo (la usamos siempre con
# .match), por lo que no necesita un marcador final para distinguirla de las
# referencias inline ("…del artículo 320 del Código…"), que nunca abren párrafo.
RE_ARTICULO = re.compile(
    r"^\s*art[ií]culo\s+(\d+[A-Za-z]?(?:-\d+)?)(?=[º°o\.\-,;:)\s]|$)", re.I
)
RE_NIVEL = re.compile(
    r"^\s*(PARTE|LIBRO|T[ÍI]TULO|SECCI[ÓO]N|CAP[ÍI]TULO)\b\s*(.*)$", re.I
)
RE_NUMERAL = re.compile(r"^\s*(\d+)\.\s+")
RE_LITERAL = re.compile(r"^\s*([a-záéíóúñ])\)\s+", re.I)
RE_PARAGRAFO = re.compile(r"^\s*par[áa]grafo\b", re.I)
RE_TITULO_NORMA = re.compile(
    r"^\s*(Ley|Decreto(?:\s+Ley)?|Resoluci[óo]n|Acuerdo|Circular|C[óo]digo)\s+"
    r"(?:Estatutaria\s+|Org[áa]nica\s+)?(\d+[A-Za-z]?)\s+de\s+(\d{4})",
    re.I,
)

# Palabras clave que delatan una nota editorial (no texto normativo).
NOTA_KEYS = (
    "derogad",
    "modificad",
    "adicionad",
    "subrogad",
    "corregid",
    "reglamentad",
    "sustituid",
    "exequible",
    "inexequible",
    "declarad",
    "condicionalmente",
    "legislación anterior",
    "texto anterior",
    "notas del editor",
    "nota del editor",
    "notas de vigencia",
    "concordancias",
    "jurisprudencia",
    "ver el art",
    "aparte",
    "expresión",
)


def _sin_tildes(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def _es_centrado(p: Tag) -> bool:
    if p.get("align", "").lower() == "center":
        return True
    style = (p.get("style") or "").lower()
    return "text-align:center" in style.replace(" ", "")


def _limpiar(p: Tag) -> Tag:
    """Quita de una copia los nodos que no son texto normativo."""
    for nodo in p.find_all(["script", "style", "img", "button"]):
        nodo.decompose()
    for nodo in p.find_all(class_=re.compile(r"card|jurisprud", re.I)):
        nodo.decompose()
    return p


def _texto(p: Tag) -> str:
    return re.sub(r"\s+", " ", p.get_text(" ", strip=True)).strip()


def _hrefs(p: Tag) -> list[HrefRef]:
    refs: list[HrefRef] = []
    for a in p.find_all("a", href=True):
        href = a["href"]
        m = re.search(r"norma\.php\?i=(\d+)(?:#(\d+))?", href)
        if m:
            refs.append(HrefRef(i=m.group(1), art=m.group(2), texto=a.get_text(strip=True)))
    return refs


# --- Detección de tipo de párrafo ------------------------------------------


def _es_nivel(texto: str) -> re.Match | None:
    m = RE_NIVEL.match(texto)
    if not m:
        return None
    # Evita falsos positivos largos (un inciso que empieza por "Título ejecutivo…").
    resto = m.group(2).strip()
    if len(texto) > 90:
        return None
    return m


def _es_nota(texto: str, p: Tag | None) -> bool:
    t = _sin_tildes(texto).lower()
    parentetica = texto.startswith("(") and texto.endswith(")")
    tiene_key = any(k in t for k in NOTA_KEYS)
    # Nota típica: parentética y con palabra clave, o párrafo con un único enlace
    # alineado a la izquierda hacia otra norma.
    if parentetica and tiene_key:
        return True
    if p is not None and parentetica and p.find("a", href=re.compile("norma.php")):
        return True
    if p is not None and p.get("align", "").lower() == "left" and tiene_key and len(texto) < 240:
        return True
    return False


def _clase_nota(texto: str) -> str:
    t = _sin_tildes(texto).lower()
    if "inexequible" in t or "deroga" in t:
        return "warning"
    if "modificad" in t or "adicionad" in t or "subrogad" in t or "sustituid" in t:
        return "info"
    return "note"


# --- Construcción de bloques de cuerpo --------------------------------------


def _bloque_de_texto(texto: str, hrefs: list[HrefRef], p: Tag | None = None) -> Bloque | None:
    """Clasifica un texto ya extraído en un :class:`Bloque`."""
    texto = texto.strip()
    if not texto:
        return None
    if _es_nota(texto, p):
        return Bloque("nota", texto, hrefs=hrefs, clase_nota=_clase_nota(texto))
    m = RE_NUMERAL.match(texto)
    if m:
        return Bloque("numeral", texto[m.end():].strip(), marca=m.group(1), hrefs=hrefs)
    m = RE_LITERAL.match(texto)
    if m:
        return Bloque("literal", texto[m.end():].strip(), marca=m.group(1), hrefs=hrefs)
    if RE_PARAGRAFO.match(texto):
        return Bloque("paragrafo", texto, hrefs=hrefs)
    return Bloque("inciso", texto, hrefs=hrefs)


def _epigrafe_y_resto(p: Tag) -> tuple[str | None, str]:
    """Separa epígrafe y texto inicial del cuerpo en la cabecera de un artículo."""
    strong = p.find("strong")
    em = strong.find("em") if strong else p.find("em")
    if em and em.get_text(strip=True):
        epi = em.get_text(strip=True).strip(" .")
        # El cuerpo inline es lo que sigue al </strong>.
        resto = ""
        if strong:
            partes = []
            for sib in strong.next_siblings:
                partes.append(sib.get_text() if isinstance(sib, Tag) else str(sib))
            resto = re.sub(r"\s+", " ", "".join(partes)).strip(" .")
        return epi, resto
    # Variante vieja: "ARTÍCULO 1°. Objeto. La presente ley…"
    return _epigrafe_de_texto(_texto(p))


def _epigrafe_de_texto(texto: str) -> tuple[str | None, str]:
    """Epígrafe + cuerpo inicial a partir de solo texto (sin Tag)."""
    t = RE_ARTICULO.sub("", texto, count=1)
    # Quita el ordinal/puntuación que el lookahead de RE_ARTICULO dejó intacto.
    t = t.lstrip(" º°o.º°:-–—\t").strip()
    # epígrafe = primera oración corta (rúbrica) antes del cuerpo.
    m = re.match(r"(.{2,80}?)\.\s+(.*)$", t, re.S)
    if m:
        return m.group(1).strip(" ."), m.group(2).strip()
    return (t.strip(" .") or None), ""


# Cabecera de artículo con ordinal (º/°): distingue encabezados reales de las
# referencias inline ("artículo 320 del…"), que carecen del ordinal.
RE_HEADER_SPLIT = re.compile(r"\bart[ií]culo\s+\d+[A-Za-z]?\s*[º°]", re.I)


def _expandir(parrafos: list[Tag]) -> list[tuple[str, Tag, bool]]:
    """Convierte los <p> en unidades, dividiendo los que acumulan varias
    cabeceras de artículo (HTML viejo sin cierres </P>).

    Devuelve tuplas ``(texto, tag, es_segmento)`` donde ``es_segmento`` indica
    que el texto proviene de partir un párrafo (no fiable para epígrafe/hrefs).
    """
    out: list[tuple[str, Tag, bool]] = []
    for p in parrafos:
        p = _limpiar(p)
        texto = _texto(p)
        if not texto:
            continue
        pos = [m.start() for m in RE_HEADER_SPLIT.finditer(texto)]
        if len(pos) >= 2:
            if pos[0] > 0:
                out.append((texto[: pos[0]].strip(), p, True))
            limites = pos[1:] + [len(texto)]
            for a, b in zip(pos, limites):
                seg = texto[a:b].strip()
                if seg:
                    out.append((seg, p, True))
        else:
            out.append((texto, p, False))
    return out


# --- Parser principal -------------------------------------------------------


def parse(html: str, *, url: str | None = None, id_fuente: str | None = None) -> Norma:
    soup = BeautifulSoup(html, "html.parser")
    norma = Norma(url_fuente=url, id_fuente=id_fuente)

    # Título de la norma (h2.titulo-norma → "Ley 1564 de 2012").
    h2 = soup.find("h2", class_="titulo-norma")
    if h2:
        norma.titulo = h2.get_text(strip=True)
        m = RE_TITULO_NORMA.match(norma.titulo)
        if m:
            norma.tipo = m.group(1).title().replace("Ley Ley", "Ley")
            norma.numero = m.group(2)
            norma.anio = m.group(3)

    cont = soup.find("div", class_="descripcion-contenido")
    if cont is None:
        raise ValueError("No se encontró div.descripcion-contenido en el HTML")

    # Recogemos los <p> más externos en orden de documento. Las páginas viejas
    # usan <P> en mayúsculas con anidación malformada (faltan cierres </P>), así
    # que tomamos los párrafos no contenidos en otro <p>, y luego dividimos los
    # que acumulan varias cabeceras de artículo. Excluimos tarjetas de
    # jurisprudencia / "texto anterior".
    _excluir = re.compile(r"card|jurisprud", re.I)
    parrafos = [
        p for p in cont.find_all("p")
        if not p.find_parent("p") and not p.find_parent(class_=_excluir)
    ]
    unidades = _expandir(parrafos)  # lista de (texto, tag, es_segmento)

    items: list = []
    articulo_actual: Articulo | None = None
    visto_primer_item = False  # ¿ya empezó la jerarquía o el articulado?

    i = 0
    while i < len(unidades):
        texto, p, es_seg = unidades[i]

        # ¿Cabecera de jerarquía? (solo en párrafos completos centrados)
        m_nivel = _es_nivel(texto)
        m_art = RE_ARTICULO.match(texto)
        if m_nivel and not m_art and not es_seg and _es_centrado(p):
            tipo_raw = _sin_tildes(m_nivel.group(1)).upper()
            tipo = {
                "TITULO": "TÍTULO",
                "SECCION": "SECCIÓN",
                "CAPITULO": "CAPÍTULO",
            }.get(tipo_raw, tipo_raw)
            etiqueta = m_nivel.group(2).strip()
            # El nombre puede venir en la siguiente unidad centrada (saltando vacíos).
            nombre = ""
            j = i + 1
            while j < len(unidades):
                t2, p2, seg2 = unidades[j]
                if not t2:
                    j += 1
                    continue
                if (
                    not seg2
                    and _es_centrado(p2)
                    and not _es_nivel(t2)
                    and not RE_ARTICULO.match(t2)
                    and p2.find("strong")
                    and len(t2) < 160
                ):
                    nombre = t2
                    i = j  # consumimos la línea de nombre
                break
            items.append(Nivel(tipo=tipo, etiqueta=etiqueta, nombre=nombre))
            articulo_actual = None
            visto_primer_item = True
            i += 1
            continue

        # ¿Cabecera de artículo?
        if m_art:
            numero = m_art.group(1).upper()
            epi, resto = _epigrafe_y_resto(p) if not es_seg else _epigrafe_de_texto(texto)
            articulo_actual = Articulo(numero=numero, epigrafe=epi)
            if resto:
                b = _bloque_de_parrafo_texto(resto, [] if es_seg else _hrefs(p))
                if b:
                    articulo_actual.bloques.append(b)
            items.append(articulo_actual)
            visto_primer_item = True
            i += 1
            continue

        # Cuerpo de artículo / preámbulo.
        bloque = _bloque_de_texto(texto, [] if es_seg else _hrefs(p), p if not es_seg else None)
        if bloque:
            if articulo_actual is not None:
                articulo_actual.bloques.append(bloque)
            else:
                norma.preambulo.append(bloque)
        i += 1

    norma.items = items
    _extraer_meta_preambulo(norma)
    return norma


def _bloque_de_parrafo_texto(texto: str, hrefs: list[HrefRef]) -> Bloque | None:
    """Clasifica el texto inline que sigue a la cabecera del artículo."""
    return _bloque_de_texto(texto, hrefs, None)


def _extraer_meta_preambulo(norma: Norma) -> None:
    """Busca epígrafe ('Por medio de la cual…') y fecha en el preámbulo."""
    for b in norma.preambulo:
        t = b.texto.strip()
        low = _sin_tildes(t).lower()
        if norma.epigrafe_norma is None and low.startswith("por "):
            norma.epigrafe_norma = t
        if norma.fecha is None and re.match(r"^\(?\s*[A-Za-zÁÉÍÓÚáéíóú]+\s+\d{1,2}\)?$", t):
            norma.fecha = t.strip("()")
