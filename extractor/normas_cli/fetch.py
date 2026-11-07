"""Descarga de normas desde el gestor normativo de Función Pública (DAFP).

La URL canónica es ``https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=<id>``.
El sitio declara ``charset=ISO-8859-1`` en el ``<meta>`` pero sirve UTF-8 en el
header HTTP (y las páginas viejas usan entidades HTML). Por eso confiamos en el
``Content-Type`` del header y, si falta, dejamos que ``requests`` infiera.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

BASE = "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php"
USER_AGENT = (
    "normas-obsidian/0.1 (+https://github.com/) extractor de normativa para Obsidian"
)


def url_para_id(i: str | int) -> str:
    return f"{BASE}?i={i}"


def id_desde_url(url: str) -> str | None:
    """Extrae el ``i=<id>`` de una URL de Función Pública."""
    q = parse_qs(urlparse(url).query)
    if "i" in q:
        return q["i"][0]
    m = re.search(r"[?&]i=(\d+)", url)
    return m.group(1) if m else None


def fetch_html(origen: str, *, timeout: int = 60) -> tuple[str, str]:
    """Devuelve ``(html, url)`` para un id, una URL o una ruta de archivo local.

    - Si ``origen`` es un número o una URL de Función Pública, descarga por HTTP.
    - Si ``origen`` apunta a un archivo existente, lo lee (útil para fixtures).
    """
    p = Path(origen)
    if p.exists():
        # Archivo local: intentamos UTF-8 y caemos a latin-1 si falla.
        data = p.read_bytes()
        try:
            return data.decode("utf-8"), str(p)
        except UnicodeDecodeError:
            return data.decode("latin-1"), str(p)

    url = origen if origen.startswith("http") else url_para_id(origen.strip())
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    resp.raise_for_status()
    # Preferimos el charset del header; si el servidor no lo da, requests usa
    # apparent_encoding (chardet) en lugar del ISO-8859-1 por defecto.
    if "charset" not in resp.headers.get("Content-Type", "").lower():
        resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text, url
