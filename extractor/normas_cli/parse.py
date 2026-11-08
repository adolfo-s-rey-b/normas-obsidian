"""Parser tolerante a variantes del HTML de Función Pública (DAFP).

Trabaja sobre el texto decodificado y clasifica los párrafos por su contenido,
apoyándose en la estructura solo donde es fiable (negrita de la cabecera,
centrado de los encabezados). Variantes verificadas:

  * CGP / CPACA:  ``<strong>ARTÍCULO 15. <em>Epígrafe</em>.</strong> texto``
  * CCo:          ``<strong>ARTÍCULO 1</strong><strong>.</strong> <strong>EPÍGRAFE</strong>. texto``
  * CST / ET:     ``<strong>ARTICULO 1. OBJETO.</strong> texto``
  * Ley 1996:     ``<strong>ARTÍCULO 1°. </strong>Objeto. texto`` (epígrafe fuera de la negrita)
  * CN:           ``<strong>ARTÍCULO 1.</strong> texto`` (sin epígrafe)
  * Decreto 2651: ``<P>`` sin cerrar, varios artículos en un mismo párrafo.

Salvaguardas principales:

  * Una cabecera solo se acepta si su número **continúa la secuencia** (evita
    tomar como artículos las enumeraciones de un artículo de derogatorias, o
    los artículos citados de otra norma).
  * La profundidad de los niveles (LIBRO/SECCIÓN/TÍTULO…) se **infiere** de la
    propia norma; puede fijarse con ``jerarquia`` en el registry.
  * Los transitorios se agrupan en series (la Constitución reinicia la
    numeración en cada Acto Legislativo).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from bs4 import BeautifulSoup, NavigableString, Tag

from .model import ORDEN_DEFECTO, Articulo, Bloque, HrefRef, Nivel, Norma

# --- Utilidades de texto ------------------------------------------------------


def _sin_tildes(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def _fold(s: str) -> str:
    """Minúsculas sin tildes, **conservando la longitud** (posiciones válidas)."""
    out = []
    for c in s:
        d = unicodedata.normalize("NFD", c)[0] if c.strip() else c
        out.append(d.lower() if len(d.lower()) == 1 else c)
    return "".join(out)


def _espacios(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _texto(t: Tag) -> str:
    return _espacios(t.get_text(" ", strip=True))


def _es_centrado(p: Tag | None) -> bool:
    if p is None:
        return False
    if (p.get("align") or "").lower() == "center":
        return True
    style = (p.get("style") or "").lower().replace(" ", "")
    return "text-align:center" in style


def _todo_negrita(p: Tag) -> bool:
    """¿Todo el texto visible del párrafo está en negrita?"""
    hay = False
    for s in p.find_all(string=True):
        if not s.strip():
            continue
        hay = True
        if not s.find_parent(["strong", "b"]):
            return False
    return hay


def _hrefs(p: Tag | None) -> list[HrefRef]:
    if p is None:
        return []
    refs: list[HrefRef] = []
    for a in p.find_all("a", href=True):
        m = re.search(r"norma\.php\?i=(\d+)(?:#([\w.-]+))?", a["href"])
        if m:
            refs.append(HrefRef(i=m.group(1), art=m.group(2), texto=a.get_text(" ", strip=True)))
    return refs


# --- Expresiones regulares ---------------------------------------------------

RE_NIVEL = re.compile(
    r"^\s*(PARTE|LIBRO|T[ÍI]TULO|SUBSECCI[ÓO]N|SECCI[ÓO]N|CAP[ÍI]TULO)"
    r"(?:\b|(?=[IVXLCDM]+\b|\d))\.?\s*(.*)$",
    re.I,
)
RE_ETIQUETA = re.compile(
    r"^(PRELIMINAR|[ÚU]NIC[OA]|TRANSITORIO|[IVXLCDM]+[A-Z]?|\d+[A-Z]?|"
    r"PRIMER[OA]?|SEGUND[OA]|TERCER[OA]?|CUART[OA]|QUINT[OA]|SEXT[OA]|S[ÉE]PTIM[OA]|"
    r"OCTAV[OA]|NOVEN[OA]|D[ÉE]CIM[OA](?:\s+(?:PRIMER[OA]?|SEGUND[OA]|TERCER[OA]?|"
    r"CUART[OA]|QUINT[OA]|SEXT[OA]|S[ÉE]PTIM[OA]|OCTAV[OA]|NOVEN[OA]))?)\b\.?\s*[-–:.]?\s*(.*)$",
    re.I,
)
RE_NUMERAL = re.compile(r"^\s*(\d{1,3})\s*[º°]?\s*[\.\)](?:\s+|$)")
RE_LITERAL = re.compile(r"^\s*([a-zñ])\)\s+", re.I)
RE_PARAGRAFO = re.compile(r"^\s*par[áa]grafo\b", re.I)
RE_TITULO_NORMA = re.compile(
    r"^\s*(Ley|Decreto(?:\s+Ley|\s+Legislativo)?|Resoluci[óo]n|Acuerdo|Circular|"
    r"Acto\s+Legislativo|Constituci[óo]n\s+Pol[íi]tica)\s+"
    r"(?:Estatutaria\s+|Org[áa]nica\s+)?(\d+[A-Za-z]?)\s+de\s+(\d{4})",
    re.I,
)
RE_FIRMA = re.compile(
    r"^(EL\s+PRESIDENTE\s+DEL?\s+(?:HONORABLE\s+)?SENADO|PUBL[ÍI]QUESE|COMUN[ÍI]QUESE|"
    r"Dada\s+en\s|CONSTANCIA\s*$)",
    re.I,
)
RE_ENVOLTURA = re.compile(r"(es el siguiente|son los siguientes|es del siguiente tenor)\s*:?\s*$", re.I)
# Nota editorial al inicio de un numeral/inciso: «Corregido por el art. 16, Decreto 1736 de 2012. Texto…»
RE_NOTA_INICIAL = re.compile(
    r"^((?:Corregido|Modificado|Adicionado|Derogado|Subrogado|Sustituido|Reglamentado)"
    r"\s+(?:por\s+)?(?:el\s+|la\s+)?(?:[^.]|(?<=\b[aA]rt)\.|(?<=\bNo)\.){0,160}?\d{4})\s*\.\s+(?=\S)",
    re.I,
)
# División de párrafos que acumulan varias cabeceras (HTML viejo sin </P>).
RE_HEADER_SPLIT = re.compile(
    r"(?:ART[ÍI]CULO|Art[íi]culo)\s+\d+[A-Z]?\s*[º°]"
    r"|(?<=[.:]\s)(?:ART[ÍI]CULO)\s+\d+[A-Z]?(?:-\d+)?\s*\.\s"
)

NOTA_KEYS = (
    "derogad", "modificad", "adicionad", "subrogad", "corregid", "reglamentad",
    "sustituid", "exequible", "inexequible", "declarad", "condicionalmente",
    "legislacion anterior", "texto anterior", "notas del editor", "nota del editor",
    "notas de vigencia", "concordancias", "jurisprudencia", "ver el art", "aparte",
    "expresion", "sentencia", "vigencia", "ver ley", "ver decreto",
)

# Palabras que, en minúscula tras «artículo N», delatan una referencia inline.
RE_NO_CABECERA = re.compile(
    r"^(?:y|e|o|u|a|al|del|de|en|inciso|incisos|numeral|numerales|literal|par[áa]grafo|"
    r"ib[íi]dem|ejusdem|se|que|y\s)\b|^[,;]"
)


# --- Cabecera de artículo ------------------------------------------------------


@dataclass
class Cabecera:
    numero: str  # "15", "397A", "115-1", "transitorio 3", "transitorio"
    fin: int  # índice en el texto donde termina "ARTÍCULO N[º]."
    transitorio: bool
    base: int  # parte numérica principal (0 si no tiene)
    clave: tuple  # para comparar orden
    # Lectura alternativa sin la letra separada por espacio («ARTÍCULO 179 A»
    # es 179A tras un 179, pero «ARTÍCULO 5 A partir de…» es el 5).
    sin_letra: "Cabecera | None" = None


RE_ART_INICIO = re.compile(r"^\s*(ART[ÍI]CULO|Art[íi]culo|ARTICULO)(S?)\s+")
RE_ART_PUNTEADO = re.compile(r"(\d{1,2}(?:\.\d{1,2}){2,9})\.?(?![\d])")
RE_ART_NUM = re.compile(r"(\d+)(?:\s*-\s*(\d+))?([A-N](?![A-Za-záéíóúñÁÉÍÓÚÑ]))?")


def _cabecera(texto: str) -> Cabecera | None:
    """Reconoce «ARTÍCULO N…» al inicio de ``texto`` (no «artículos», no minúscula)."""
    m = RE_ART_INICIO.match(texto)
    if not m:
        return None
    pos = m.end()
    resto = texto[pos:]
    transitorio = False
    mt = re.match(r"(TRANSITORIO|Transitorio)\b\s*", resto)
    if mt:
        transitorio = True
        pos += mt.end()
        resto = texto[pos:]
    # Numeración punteada de los decretos únicos: «ARTÍCULO 2.2.1.1.1.1.1.»
    md = RE_ART_PUNTEADO.match(resto)
    if md and not transitorio:
        partes = [int(x) for x in md.group(1).split(".")]
        fin = pos + md.end()
        despues = texto[fin:]
        if RE_NO_CABECERA.match(despues.lstrip()):
            return None
        return Cabecera(md.group(1), fin, False, partes[0], tuple(partes) + (0,) * (10 - len(partes)))
    mn = RE_ART_NUM.match(resto)
    if not mn:
        if transitorio:  # «ARTÍCULO TRANSITORIO.» sin número
            fin = pos + len(resto) - len(resto.lstrip(" .:-–—"))
            return Cabecera("transitorio", fin, True, 0, (0, 0, 0))
        return None
    base = int(mn.group(1))
    sub = int(mn.group(2)) if mn.group(2) else 0
    letra = mn.group(3) or ""
    numero = f"{base}" + (f"-{sub}" if mn.group(2) else "") + letra
    fin = pos + mn.end()
    despues = texto[fin:]
    # Ordinal pegado: 1º, 1°, 1o. (la «o» solo si no sigue una letra)
    mo = re.match(r"\s*(?:[º°]|o(?![a-záéíóúñ]))", despues)
    if mo:
        fin += mo.end()
        despues = texto[fin:]
    if RE_NO_CABECERA.match(despues.lstrip()):
        return None
    if m.group(2) and not re.match(r"\s*\.\s", despues):
        return None  # «ARTICULOS 93, 94 y 95» no es una cabecera
    alternativa = None
    if not letra and not transitorio:
        ml = re.match(r"\s([A-N])(?=[\s.:-]|$)", despues)
        if ml:
            alternativa = Cabecera(numero, fin, False, base, (base, sub, 0))
            letra = ml.group(1)
            numero += letra
            fin += ml.end()
    if transitorio:
        numero = f"transitorio {numero}"
    letra_ord = (ord(letra) - 64) if letra else 0
    return Cabecera(numero, fin, transitorio, base, (base, sub, letra_ord), alternativa)


# --- Unidades del documento ----------------------------------------------------


@dataclass
class Unidad:
    texto: str
    tag: Tag | None  # None si es un segmento de un párrafo partido
    tabla: str | None = None  # markdown si la unidad es una tabla

    @property
    def es_segmento(self) -> bool:
        return self.tag is None


_EXCLUIR = re.compile(r"card|jurisprud", re.I)


def _tabla_md(t: Tag) -> str:
    filas = []
    for tr in t.find_all("tr"):
        if tr.find_parent("table") is not t:
            continue
        celdas = [_espacios(c.get_text(" ", strip=True)).replace("|", "\\|")
                  for c in tr.find_all(["td", "th"])]
        if any(celdas):
            filas.append(celdas)
    if not filas:
        return ""
    ancho = max(len(f) for f in filas)
    filas = [f + [""] * (ancho - len(f)) for f in filas]
    lineas = ["| " + " | ".join(filas[0]) + " |", "|" + " --- |" * ancho]
    lineas += ["| " + " | ".join(f) + " |" for f in filas[1:]]
    return "\n".join(lineas)


def _unidades(cont: Tag) -> list[Unidad]:
    out: list[Unidad] = []
    for el in cont.find_all(["p", "table", "li"]):
        if el.decomposed or el.attrs is None:
            continue
        if el.find_parent(class_=_EXCLUIR) or _EXCLUIR.search(" ".join(el.get("class") or [])):
            continue
        if el.name == "table":
            if el.find_parent("table"):
                continue
            md = _tabla_md(el)
            if md:
                out.append(Unidad(_espacios(el.get_text(" ", strip=True)), el, md))
            continue
        if el.name == "li":
            if el.find_parent(["p", "table", "li"]):
                continue
            texto = _texto(el)
            lista = el.find_parent(["ol", "ul"])
            if texto and lista is not None and lista.name == "ol":
                hermanos = [x for x in lista.find_all("li", recursive=False)]
                try:
                    inicio = int(lista.get("start") or 1)
                except ValueError:
                    inicio = 1
                n = inicio + (hermanos.index(el) if el in hermanos else 0)
                if (lista.get("type") or "1") in ("a", "A"):
                    texto = f"{chr(96 + n)}) {texto}"
                elif not RE_NUMERAL.match(texto):
                    texto = f"{n}. {texto}"
            if texto:
                out.append(Unidad(texto, el))
            continue
        if el.find_parent("p") or el.find_parent("table") or el.find_parent("li"):
            continue
        for nodo in el.find_all(["script", "style", "img", "button"]):
            nodo.decompose()
        for nodo in el.find_all(class_=_EXCLUIR):
            nodo.decompose()
        texto = _texto(el)
        if not texto:
            continue
        pos = [m.start() for m in RE_HEADER_SPLIT.finditer(texto)
               if _cabecera(texto[m.start():]) is not None]
        if len(pos) >= 2 or (pos and pos[0] > 0):
            if pos[0] > 0:
                out.append(Unidad(texto[: pos[0]].strip(), None))
            for a, b in zip(pos, pos[1:] + [len(texto)]):
                seg = texto[a:b].strip()
                if seg:
                    out.append(Unidad(seg, None))
        else:
            out.append(Unidad(texto, el))
    return out


# --- Notas editoriales ---------------------------------------------------------


def _es_nota(texto: str, p: Tag | None) -> bool:
    t = _sin_tildes(texto).lower()
    limpio = texto.strip().rstrip(".").strip()
    parentetica = limpio.startswith("(") and limpio.endswith(")")
    tiene_key = any(k in t for k in NOTA_KEYS)
    if parentetica and (tiene_key or t.startswith("(ver") or t.startswith("( ver")):
        return True
    if p is not None and parentetica and p.find("a", href=re.compile("norma.php")):
        return True
    if p is not None and (p.get("align") or "").lower() == "left" and tiene_key and len(texto) < 240:
        return True
    return False


def clase_nota(texto: str) -> str:
    t = _sin_tildes(texto).lower()
    if "inexequible" in t or "deroga" in t:
        return "warning"
    if any(k in t for k in ("modificad", "adicionad", "subrogad", "sustituid", "corregid")):
        return "info"
    return "note"


def _nota(texto: str, hrefs: list[HrefRef]) -> Bloque:
    return Bloque("nota", texto, hrefs=hrefs, clase_nota=clase_nota(texto))


# --- Bloques de cuerpo -----------------------------------------------------------


def _bloques_de_texto(texto: str, hrefs: list[HrefRef], p: Tag | None = None) -> list[Bloque]:
    """Clasifica un texto en uno o dos bloques (nota inicial + contenido)."""
    texto = texto.strip()
    if not texto:
        return []
    if _es_nota(texto, p):
        return [_nota(texto, hrefs)]
    previos: list[Bloque] = []
    marca = None
    tipo = "inciso"
    m = RE_NUMERAL.match(texto)
    if m:
        tipo, marca, texto = "numeral", m.group(1), texto[m.end():].strip()
    else:
        m = RE_LITERAL.match(texto)
        if m:
            tipo, marca, texto = "literal", m.group(1), texto[m.end():].strip()
    mn = RE_NOTA_INICIAL.match(texto)
    if mn and any(k in _sin_tildes(mn.group(1)).lower() for k in NOTA_KEYS):
        previos.append(_nota(mn.group(1).strip(), [h for h in hrefs if h.texto in mn.group(1)]))
        texto = texto[mn.end():].strip()
    if tipo == "inciso" and RE_PARAGRAFO.match(texto):
        tipo = "paragrafo"
    return previos + [Bloque(tipo, texto, marca=marca, hrefs=hrefs)]


def _partir_cabecera(u: Unidad, cab: Cabecera) -> tuple[str | None, str, list[Bloque]]:
    """Devuelve ``(epígrafe, cuerpo inicial, notas de cabecera)``.

    Usa la negrita inicial del párrafo como ámbito del epígrafe: todo lo que
    está en negrita tras «ARTÍCULO N.» es rúbrica; lo demás es cuerpo.
    """
    negrita, resto = "", u.texto[cab.fin:]
    if u.tag is not None:
        partes_n, partes_r, en_negrita = [], [], True
        for s in u.tag.find_all(string=True):
            if not isinstance(s, NavigableString):
                continue
            txt = str(s)
            if en_negrita:
                bold = s.find_parent(["strong", "b", "em", "i"]) is not None
                if bold or not re.search(r"\w", txt):
                    partes_n.append(txt)
                    continue
                en_negrita = False
            partes_r.append(txt)
        negrita = _espacios("".join(partes_n))
        cab_n = _cabecera(negrita)
        if cab_n is not None:
            negrita = negrita[cab_n.fin:]
            resto = _espacios("".join(partes_r))
        else:
            negrita = ""
    # Notas entre paréntesis dentro de la rúbrica: «(Adicionado por el art. 3…)».
    notas: list[Bloque] = []
    hrefs = _hrefs(u.tag)

    def _extraer(mm: re.Match) -> str:
        if any(k in _sin_tildes(mm.group(0)).lower() for k in NOTA_KEYS):
            notas.append(_nota(mm.group(0), [h for h in hrefs if h.texto and h.texto in mm.group(0)]))
            return " "
        return mm.group(0)

    negrita = re.sub(r"\([^()]*\)", _extraer, negrita)
    epi = _espacios(negrita).strip(" .:-–—")
    cuerpo = _espacios(resto).lstrip(" .:-–—")
    mn = RE_EPI_NOTA.match(epi)
    if mn:
        notas.append(_nota(mn.group(1), [h for h in hrefs if h.texto and h.texto in mn.group(1)]))
        epi = mn.group(2).strip(" .:-–—")
    if epi:
        # Negrita que abarca rúbrica y cuerpo: «OBJETO. La ley regula…»
        mm = re.match(r"(.{2,200}?)\.\s+(.*[a-záéíóúñ].*)$", epi)
        if mm and mm.group(1).upper() == mm.group(1):
            epi, cuerpo = mm.group(1).strip(), _espacios(mm.group(2) + " " + cuerpo)
        elif len(epi) > 250 or RE_EPI_REFORMA.match(epi) or RE_INTRO_CITA.search(epi):
            # «Modifíquese el parágrafo 2 … el cual quedará así:» en negrita es
            # texto del artículo (reformatorio), no su rúbrica.
            epi, cuerpo = "", _espacios(epi + " " + cuerpo)
    return (epi or None), cuerpo, notas


RE_EPI_REFORMA = re.compile(r"^(?:modif|adici|der[óo]g|sustit|subr[óo]g|reempl|incorp)\w*se\b", re.I)
# Nota editorial pegada al inicio de la rúbrica, sin paréntesis:
# «Derogado por el art. 49 Ley 640 de 2001Clases», «Adicionado por … de 2008, así: OMISIÓN…»
RE_EPI_NOTA = re.compile(
    r"^((?:Corregido|Modificado|Adicionado|Derogado|Subrogado|Sustituido|Reglamentado)\s+"
    r"(?:parcialmente\s+)?por\s+.{0,160}?\d{4})\s*(?:,?\s*as[ií]\s*:)?\s*[.:-]?\s*(.*)$",
    re.I | re.S,
)


RE_EPI_TEXTO = re.compile(r"^(.{2,160}?)\.\s+(?=[A-ZÁÉÍÓÚÑ\"“(¿¡])(.*)$", re.S)


def _epigrafe_en_texto(cuerpo: str) -> tuple[str, str] | None:
    m = RE_EPI_TEXTO.match(cuerpo)
    if m and len(m.group(1).split()) <= 20 and not re.search(r"\d{3,}", m.group(1)):
        return m.group(1).strip(), m.group(2).strip()
    return None


# --- Niveles -------------------------------------------------------------------


_TIPOS = {"TITULO": "TÍTULO", "SECCION": "SECCIÓN", "SUBSECCION": "SUBSECCIÓN", "CAPITULO": "CAPÍTULO"}


def _nivel(u: Unidad) -> tuple[str, str, str] | None:
    """``(tipo, etiqueta, nombre)`` si la unidad es un encabezado de jerarquía."""
    if u.es_segmento or u.tabla or len(u.texto) > 160:
        return None
    m = RE_NIVEL.match(u.texto)
    if not m or not (_es_centrado(u.tag) or _todo_negrita(u.tag)):
        return None
    tipo_raw = _sin_tildes(m.group(1)).upper()
    tipo = _TIPOS.get(tipo_raw, tipo_raw)
    resto = m.group(2).strip()
    if not resto:
        return tipo, "", ""
    me = RE_ETIQUETA.match(resto)
    if not me:
        return None
    etiqueta = me.group(1).upper().rstrip(".")
    nombre = me.group(2).strip(" .-–:\"“”'")
    return tipo, etiqueta, nombre


def _es_rubro(u: Unidad) -> bool:
    """Encabezado sin etiqueta: centrado, en negrita, corto y no normativo."""
    if u.es_segmento or u.tabla or not u.texto or len(u.texto) > 160:
        return False
    if not _es_centrado(u.tag) or not _todo_negrita(u.tag):
        return False
    if _cabecera(u.texto) or RE_FIRMA.match(u.texto) or _es_nota(u.texto, u.tag):
        return False
    letras = [c for c in u.texto if c.isalpha()]
    return bool(letras)


def _inferir_orden(niveles_seq: list[tuple[Nivel, bool]], forzado: list[str] | None) -> list[str]:
    """Orden de los tipos de nivel presentes, de mayor a menor.

    ``niveles_seq`` es la secuencia de (nivel, hubo_articulos_desde_el_anterior).
    Un encabezado seguido inmediatamente de otro (sin artículos entre medias)
    es evidencia de que el primero contiene al segundo.
    """
    presentes: list[str] = []
    for n, _ in niveles_seq:
        if n.tipo != "RUBRO" and n.tipo not in presentes:
            presentes.append(n.tipo)
    if forzado:
        orden = [t for t in forzado if t in presentes]
        return orden + [t for t in presentes if t not in orden] + ["RUBRO"]
    votos: dict[tuple[str, str], int] = {}
    prev: Nivel | None = None
    for n, hubo_art in niveles_seq:
        if prev is not None and not hubo_art and n.tipo != prev.tipo \
                and "RUBRO" not in (n.tipo, prev.tipo) and not prev.es_preliminar:
            votos[(prev.tipo, n.tipo)] = votos.get((prev.tipo, n.tipo), 0) + 1
        prev = n

    # Relación «contiene» con cierre transitivo (LIBRO>SECCIÓN y SECCIÓN>TÍTULO
    # implican LIBRO>TÍTULO); el orden por defecto solo decide lo no relacionado.
    rel = {(a, b): votos.get((a, b), 0) > votos.get((b, a), 0)
           for a in presentes for b in presentes if a != b}
    for k in presentes:
        for a in presentes:
            for b in presentes:
                if a != b and rel.get((a, k)) and rel.get((k, b)):
                    rel[(a, b)] = True

    def gana(a: str, b: str) -> bool:  # ¿a va por encima de b?
        if rel.get((a, b)) != rel.get((b, a)):
            return bool(rel.get((a, b)))
        return ORDEN_DEFECTO.index(a) < ORDEN_DEFECTO.index(b)

    restantes, orden = list(presentes), []
    while restantes:
        cand = [a for a in restantes if not any(gana(b, a) for b in restantes if b != a)]
        elegido = cand[0] if cand else min(restantes, key=ORDEN_DEFECTO.index)
        orden.append(elegido)
        restantes.remove(elegido)
    return orden + ["RUBRO"]


# --- Parser principal ------------------------------------------------------------


def parse(
    html: str,
    *,
    url: str | None = None,
    id_fuente: str | None = None,
    opciones: dict | None = None,
) -> Norma:
    """Convierte el HTML de una norma del DAFP en una :class:`Norma`.

    ``opciones`` (del registry): ``jerarquia`` (orden forzado de niveles),
    ``esquema`` (lista de niveles a insertar antes de ciertos artículos, para
    páginas sin encabezados fiables), ``nombre`` (nombre largo).
    """
    opciones = opciones or {}
    # html5lib repara el anidamiento roto como un navegador (p. ej. <B><P>Artículo 6º</B> texto</P>
    # en páginas antiguas), donde html.parser deja el texto fuera del párrafo.
    soup = BeautifulSoup(html, "html5lib")
    norma = Norma(url_fuente=url, id_fuente=id_fuente, nombre_largo=opciones.get("nombre"))

    h2 = soup.find("h2", class_="titulo-norma")
    if h2:
        norma.titulo = _espacios(h2.get_text(" ", strip=True))
        m = RE_TITULO_NORMA.match(norma.titulo)
        if m:
            norma.tipo = " ".join(w.capitalize() for w in _espacios(m.group(1)).split())
            norma.numero = m.group(2)
            norma.anio = m.group(3)

    cont = soup.find("div", class_="descripcion-contenido")
    if cont is None:
        raise ValueError("No se encontró div.descripcion-contenido en el HTML")

    unidades = _unidades(cont)
    aceptadas = _cabeceras_aceptadas(unidades, norma)

    items: list = []
    actual: Articulo | None = None
    visto = False  # ¿empezó el articulado o la jerarquía?
    en_firmas = False
    envoltura_ids: set[int] = aceptadas.pop("envoltura")  # type: ignore[assignment]
    sin_epi: list[Articulo] = []  # artículos cuya rúbrica podría estar en el texto
    niveles_seq: list[tuple[Nivel, bool]] = []
    hubo_art = False
    usar_esquema = bool(opciones.get("esquema"))
    nombre_largo_f = _fold(norma.nombre_largo or "").strip(" .")

    i = 0
    while i < len(unidades):
        u = unidades[i]
        cab = aceptadas.get(i)

        if cab is not None:
            en_firmas = False
            if u.es_segmento:
                epi, notas = None, []
                cuerpo = _espacios(u.texto[cab.fin:]).lstrip(" .:-–—")
                me = re.match(r"([A-ZÁÉÍÓÚÑÜ0-9 ,;()\-–]{3,200}?)\.\s+(.+)$", cuerpo)
                if me and re.search(r"[A-Z]{3}", me.group(1)):
                    epi, cuerpo = me.group(1).strip(), me.group(2)
            else:
                epi, cuerpo, notas = _partir_cabecera(u, cab)
            art = Articulo(numero=cab.numero, epigrafe=epi, notas_cabecera=notas)
            if cuerpo:
                art.bloques.extend(_bloques_de_texto(cuerpo, [] if u.es_segmento else _hrefs(u.tag)))
            if epi is None and cuerpo:
                sin_epi.append(art)
            if i in envoltura_ids:
                norma.envoltura.append(art)
            else:
                items.append(art)
                hubo_art = True
            actual = art
            visto = True
            i += 1
            continue

        if visto and not u.es_segmento and RE_FIRMA.match(u.texto):
            en_firmas = True
        if en_firmas:
            norma.firmas.append(u.texto)
            i += 1
            continue

        niv = None if usar_esquema else _nivel(u)
        if niv is not None:
            tipo, etiqueta, nombre = niv
            nivel = Nivel(tipo=tipo, etiqueta=etiqueta, nombre=nombre)
            j = i + 1
            if not etiqueta and j < len(unidades):  # «SECCIÓN» / «TERCERA» / nombre
                me = RE_ETIQUETA.match(unidades[j].texto.strip())
                if me and len(unidades[j].texto) < 40:
                    nivel.etiqueta = me.group(1).upper().rstrip(".")
                    nivel.nombre = nombre = me.group(2).strip(" .-–:")
                    j += 1
            while j < len(unidades):
                u2 = unidades[j]
                if _es_nota(u2.texto, u2.tag) and _es_centrado(u2.tag):
                    nivel.notas.append(_nota(u2.texto, _hrefs(u2.tag)))
                    j += 1
                    continue
                if not nombre and not u2.es_segmento and (_es_centrado(u2.tag) or _todo_negrita(u2.tag)) \
                        and j not in aceptadas and _nivel(u2) is None \
                        and len(u2.texto) < 220 and not RE_FIRMA.match(u2.texto):
                    nivel.nombre = u2.texto.strip(" .")
                    j += 1
                break
            items.append(nivel)
            niveles_seq.append((nivel, hubo_art))
            hubo_art = False
            actual = None
            visto = True
            i = j
            continue

        if visto and not usar_esquema and _es_rubro(u) \
                and _fold(u.texto).strip(" .") != nombre_largo_f:
            rubro = Nivel(tipo="RUBRO", etiqueta="", nombre=u.texto.strip(" ."))
            items.append(rubro)
            niveles_seq.append((rubro, hubo_art))
            actual = None
            i += 1
            continue

        if u.tabla:
            bloques = [Bloque("tabla", u.tabla)]
        else:
            bloques = _bloques_de_texto(u.texto, [] if u.es_segmento else _hrefs(u.tag), u.tag)
        if actual is not None:
            actual.bloques.extend(bloques)
        elif not visto:
            norma.preambulo.extend(bloques)
        elif items and isinstance(items[-1], Nivel) and all(b.tipo == "nota" for b in bloques):
            items[-1].notas.extend(bloques)
        else:
            norma.preambulo.extend(bloques)  # texto suelto entre niveles
        i += 1

    # Rúbrica en el texto (variante Ley 1996): solo si es el patrón dominante.
    def _primero(a: Articulo) -> int | None:
        k = next((k for k, b in enumerate(a.bloques) if b.tipo != "nota"), None)
        return k if k is not None and a.bloques[k].tipo == "inciso" else None

    candidatos = [a for a in sin_epi if _primero(a) is not None
                  and _epigrafe_en_texto(a.bloques[_primero(a)].texto)]  # type: ignore[index]
    if len(sin_epi) >= 3 and len(candidatos) / len(sin_epi) >= 0.7:
        for a in candidatos:
            k = _primero(a)
            epi, resto = _epigrafe_en_texto(a.bloques[k].texto)  # type: ignore[misc,index]
            a.epigrafe = epi
            if resto:
                a.bloques[k] = _bloques_de_texto(resto, a.bloques[k].hrefs)[-1]  # type: ignore[index]
            else:
                a.bloques.pop(k)  # type: ignore[arg-type]

    norma.items = items
    _series_transitorias(norma)
    if usar_esquema:
        _aplicar_esquema(norma, opciones["esquema"])
        niveles_seq = [(n, False) for n in norma.niveles]
    norma.orden_niveles = _inferir_orden(niveles_seq, opciones.get("jerarquia"))
    _asignar_profundidad(norma)
    _extraer_meta_preambulo(norma)
    return norma


RE_CITA_ARTICULO = re.compile(r"^\s*[\"“]\s*(?:ART[ÍI]CULO|Art[íi]culo)\s+\d")
RE_INTRO_CITA = re.compile(r"(?:as[íi]|siguiente|siguientes|tenor)\s*:\s*[\"“]?\s*$", re.I)
RE_VERBO_CITA = re.compile(
    r"\b(?:modif[íi]c[ae]se|adici[óo]n[ae]se|sustit[úu]y[ae]se|subr[óo]g[ae]se|reempl[áa]z[ae]se|"
    r"quedar[áa]n?)\b",
    re.I,
)


def _cabeceras_aceptadas(unidades: list[Unidad], norma: Norma) -> dict:
    """Decide qué cabeceras candidatas son artículos reales.

    Devuelve ``{indice_unidad: Cabecera, "envoltura": set(indices)}``.
    """
    cands = [(k, c) for k, u in enumerate(unidades) if not u.tabla
             for c in [_cabecera(u.texto)] if c is not None]
    acept: dict = {}
    envoltura: set[int] = set()
    ultimo: Cabecera | None = None
    ultimo_trans: Cabecera | None = None
    env_ult = 0  # último artículo de la norma envoltura
    ultimo_fue_trans = False
    k_previo = -1

    def en_cita(k: int) -> bool:
        """¿La cabecera k está dentro de un texto citado de otra norma?

        Señales desde la cabecera anterior: un párrafo que empieza con
        «"ARTÍCULO N» o un párrafo que termina en «…así:» con verbo de reforma.
        """
        for u in unidades[k_previo + 1: k]:
            if RE_CITA_ARTICULO.match(u.texto):
                return True
        previo = next((u.texto for u in reversed(unidades[k_previo + 1: k]) if u.texto), "")
        if not previo and k_previo >= 0:
            previo = unidades[k_previo].texto
        return bool(RE_INTRO_CITA.search(previo) and RE_VERBO_CITA.search(previo))

    for pos, (k, c) in enumerate(cands):
        sig = [cc for _, cc in cands[pos + 1: pos + 4]]
        if c.sin_letra is not None and not (ultimo is not None and c.base == ultimo.base):
            c = c.sin_letra
        if c.numero == "transitorio" and not ultimo_fue_trans:
            # «ARTÍCULO TRANSITORIO.» sin número entre artículos ordinarios: es
            # un inciso añadido al artículo anterior por un acto reformatorio.
            continue
        if k in acept:
            continue
        ultimo_fue_trans = c.transitorio
        if c.transitorio:
            if ultimo_trans is None or c.numero == "transitorio" or c.base == 1 \
                    or c.clave > ultimo_trans.clave:
                if ultimo_trans is not None and c.base > ultimo_trans.base + 30 \
                        and not any(s.transitorio and 0 < s.base - c.base <= 3 for s in sig):
                    norma.avisos.append(f"cabecera descartada (salto): {unidades[k].texto[:60]}")
                    continue
                acept[k] = c
                ultimo_trans = c
            else:
                norma.avisos.append(f"cabecera descartada (secuencia): {unidades[k].texto[:60]}")
            continue
        if ultimo is None:
            acept[k] = c
            ultimo = c
            k_previo = k
            if RE_ENVOLTURA.search(unidades[k].texto):
                envoltura.add(k)
                env_ult = c.base
                ultimo = None
            continue
        continua = 0 <= c.base - ultimo.base <= 3 and c.clave > ultimo.clave
        if not continua and en_cita(k):
            norma.avisos.append(f"cabecera descartada (texto citado): {unidades[k].texto[:60]}")
            continue
        if c.clave > ultimo.clave:
            salto = c.base - ultimo.base
            if salto > 30 and not any(not s.transitorio and 0 < s.base - c.base <= 3 for s in sig):
                norma.avisos.append(f"cabecera descartada (salto {salto}): {unidades[k].texto[:60]}")
                continue
            # Un salto con la secuencia actual continuando poco después es una
            # interpolación (p. ej. el texto citado del artículo reformado).
            prox = [cc for _, cc in cands[pos + 1: pos + 16] if not cc.transitorio]
            if salto > 3 and any(ultimo.base < s.base <= ultimo.base + 3 and s.base < c.base for s in prox):
                norma.avisos.append(f"cabecera descartada (interpolada): {unidades[k].texto[:60]}")
                continue
            acept[k] = c
            ultimo = c
            k_previo = k
        elif envoltura and c.base == env_ult + 1:
            acept[k] = c
            envoltura.add(k)
            env_ult = c.base
        else:
            norma.avisos.append(f"cabecera descartada (secuencia): {unidades[k].texto[:60]}")
    acept["envoltura"] = envoltura
    return acept


def _acto_de(arts: list[Articulo]) -> str | None:
    """Acto reformatorio más citado en las notas de ``arts`` («AL 1 de 2017»)."""
    cuenta: dict[str, int] = {}
    for a in arts:
        for b in a.bloques + a.notas_cabecera:
            for m in re.finditer(r"Acto\s+Legislativo\s+(?:No\.?\s*)?0?(\d+)\s+de\s+(\d{4})",
                                 b.texto, re.I):
                if b.tipo == "nota":
                    k = f"AL {m.group(1)} de {m.group(2)}"
                    peso = 10 if "adicionad" in b.texto.lower() else 1
                    cuenta[k] = cuenta.get(k, 0) + peso
    return max(cuenta, key=cuenta.get) if cuenta else None


def _series_transitorias(norma: Norma) -> None:
    """Da nombres únicos a los artículos transitorios.

    * La primera serie numerada conserva «transitorio N».
    * Las series que reinician la numeración (Actos Legislativos posteriores)
      reciben el acto que las adicionó: «transitorio 1 (AL 1 de 2017)».
    * Los transitorios sin número toman el acto de su propia nota:
      «transitorio (AL 1 de 2016)», «transitorio (AL 1 de 2016) 2»…
    """
    series: list[list[Articulo]] = []
    sueltos: list[Articulo] = []
    ultimo = None
    for a in norma.articulos:
        if not a.es_transitorio:
            continue
        num = a.numero.replace("transitorio", "").strip()
        if not num:
            sueltos.append(a)
            continue
        base = int(re.match(r"\d+", num).group())
        if ultimo is None or base <= ultimo:
            series.append([])
        series[-1].append(a)
        ultimo = base
    for k, serie in enumerate(series[1:], start=2):
        etiqueta = _acto_de(serie) or f"serie {k}"
        for a in serie:
            a.numero = f"{a.numero} ({etiqueta})"
    grupos: dict[str, list[Articulo]] = {}
    for a in sueltos:
        texto0 = a.bloques[0].texto if a.bloques else ""
        etiqueta = "final" if texto0.upper().startswith("(FINAL") else (_acto_de([a]) or "sin número")
        grupos.setdefault(etiqueta, []).append(a)
    for etiqueta, arts in grupos.items():
        for n, a in enumerate(arts, start=1):
            a.numero = f"transitorio ({etiqueta})" + (f" {n}" if len(arts) > 1 else "")


def _aplicar_esquema(norma: Norma, esquema: list[dict]) -> None:
    """Reemplaza los niveles por los del esquema del registry."""
    arts = [it for it in norma.items if isinstance(it, Articulo)]
    por_num = {a.numero: a for a in arts}
    antes: dict[int, list[Nivel]] = {}
    for e in esquema:
        a = por_num.get(str(e["antes"]))
        if a is None:
            norma.avisos.append(f"esquema: no existe el artículo {e['antes']}")
            continue
        antes.setdefault(id(a), []).append(
            Nivel(tipo=e["tipo"], etiqueta=str(e.get("etiqueta", "")), nombre=e.get("nombre", ""))
        )
    items: list = []
    for a in arts:
        items.extend(antes.get(id(a), []))
        items.append(a)
    norma.items = items


def _asignar_profundidad(norma: Norma) -> None:
    orden = norma.orden_niveles
    niveles = norma.niveles
    for n in niveles:
        if n.tipo == "RUBRO":
            n.profundidad = len(orden)
        else:
            n.profundidad = orden.index(n.tipo) if n.tipo in orden else len(orden) - 1
    # «TÍTULO PRELIMINAR» es hermano de los niveles que le siguen (p. ej. los
    # LIBROS del CGP o del CCo), no su padre.
    for k, n in enumerate(niveles):
        if n.es_preliminar:
            sig = next((x for x in niveles[k + 1:] if not x.es_preliminar and x.tipo != "RUBRO"), None)
            n.profundidad = sig.profundidad if sig else 0


def _extraer_meta_preambulo(norma: Norma) -> None:
    """Epígrafe de la norma, fecha y fecha de actualización del DAFP."""
    for b in norma.preambulo:
        t = b.texto.strip()
        sin_comillas = t.strip("\"“”' ")
        low = _sin_tildes(sin_comillas).lower()
        if norma.epigrafe_norma is None and low.startswith("por ") and len(t) > 15:
            norma.epigrafe_norma = sin_comillas
        if norma.fecha is None and re.match(r"^\(?\s*[A-Za-zÁÉÍÓÚáéíóú]+\s+\d{1,2}\s*\)?$", t):
            norma.fecha = t.strip("() ")
        m = re.match(r"^ACTUALIZACI[ÓO]N\s*:?\s*(.+)$", t, re.I)
        if m and norma.actualizacion_fuente is None:
            norma.actualizacion_fuente = m.group(1).strip().capitalize()
