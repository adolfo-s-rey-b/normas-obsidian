"""Descarga de normas desde el gestor normativo de Función Pública (DAFP).

La URL canónica es ``https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=<id>``.

Particularidades del servidor:

* Declara ``charset=ISO-8859-1`` en el ``<meta>`` pero sirve UTF-8 en el header
  HTTP. Confiamos en el ``Content-Type`` del header.
* Envía una cadena TLS incompleta (la hoja de Let's Encrypt acompañada de un
  intermedio que no le corresponde), así que la verificación estándar falla con
  ``CERTIFICATE_VERIFY_FAILED``. Igual que hacen los navegadores, descargamos el
  intermedio correcto desde la URL *CA Issuers* (AIA) del propio certificado y
  verificamos la cadena completa contra las raíces de ``certifi``. **Nunca** se
  desactiva la verificación TLS.
"""

from __future__ import annotations

import re
import ssl
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import certifi
import requests
from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509.oid import AuthorityInformationAccessOID, ExtensionOID

BASE = "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php"
REPO_URL = "https://github.com/adolfo-s-rey-b/normas-obsidian"
USER_AGENT = f"normas-obsidian/0.2 (+{REPO_URL}) extractor de normativa para Obsidian"

CACHE_DIR = Path.home() / ".cache" / "normas-obsidian"


def url_para_id(i: str | int) -> str:
    return f"{BASE}?i={i}"


def id_desde_url(url: str) -> str | None:
    """Extrae el ``i=<id>`` de una URL de Función Pública."""
    q = parse_qs(urlparse(url).query)
    if "i" in q:
        return q["i"][0]
    m = re.search(r"[?&]i=(\d+)", url)
    return m.group(1) if m else None


# --- TLS: completar la cadena con el intermedio del AIA ----------------------


def _intermedio_aia(host: str, port: int = 443) -> bytes | None:
    """PEM del emisor de la hoja de ``host`` según su extensión AIA.

    El certificado descargado aquí NO se confía por sí mismo: solo se añade al
    conjunto de candidatos y ``requests`` verifica la cadena completa hasta una
    raíz de ``certifi``.
    """
    pem_hoja = ssl.get_server_certificate((host, port), timeout=30)
    hoja = x509.load_pem_x509_certificate(pem_hoja.encode())
    try:
        aia = hoja.extensions.get_extension_for_oid(
            ExtensionOID.AUTHORITY_INFORMATION_ACCESS
        ).value
    except x509.ExtensionNotFound:
        return None
    for desc in aia:
        if desc.access_method == AuthorityInformationAccessOID.CA_ISSUERS:
            r = requests.get(desc.access_location.value, timeout=30,
                             headers={"User-Agent": USER_AGENT})
            r.raise_for_status()
            try:
                cert = x509.load_der_x509_certificate(r.content)
            except ValueError:
                cert = x509.load_pem_x509_certificate(r.content)
            return cert.public_bytes(Encoding.PEM)
    return None


def _bundle_con_aia(host: str) -> str:
    """Ruta a un bundle ``certifi`` + intermedio AIA de ``host`` (cacheado)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    destino = CACHE_DIR / f"ca-{host}.pem"
    if destino.exists() and time.time() - destino.stat().st_mtime < 7 * 86400:
        return str(destino)
    inter = _intermedio_aia(host)
    base = Path(certifi.where()).read_bytes()
    destino.write_bytes(base + b"\n" + (inter or b""))
    return str(destino)


def _get(url: str, *, timeout: int) -> requests.Response:
    headers = {"User-Agent": USER_AGENT}
    try:
        return requests.get(url, headers=headers, timeout=timeout)
    except requests.exceptions.SSLError:
        host = urlparse(url).hostname or ""
        return requests.get(url, headers=headers, timeout=timeout,
                            verify=_bundle_con_aia(host))


# --- API pública -------------------------------------------------------------


def fetch_html(
    origen: str,
    *,
    timeout: int = 90,
    cache_dir: str | Path | None = None,
    reintentos: int = 3,
) -> tuple[str, str]:
    """Devuelve ``(html, url)`` para un id, una URL o una ruta de archivo local.

    - Si ``origen`` apunta a un archivo existente, lo lee (fixtures o HTML
      guardado desde el navegador).
    - Si es un número o una URL de Función Pública, descarga por HTTP. Con
      ``cache_dir`` guarda/reutiliza ``<id>.html`` ahí.
    """
    p = Path(origen)
    if p.exists():
        data = p.read_bytes()
        try:
            return data.decode("utf-8"), str(p)
        except UnicodeDecodeError:
            return data.decode("latin-1"), str(p)

    url = origen if origen.startswith("http") else url_para_id(origen.strip())
    cache = None
    if cache_dir:
        i = id_desde_url(url)
        if i:
            cache = Path(cache_dir) / f"{i}.html"
            if cache.exists():
                return cache.read_text(encoding="utf-8"), url

    ultimo: Exception | None = None
    for intento in range(reintentos):
        try:
            resp = _get(url, timeout=timeout)
            resp.raise_for_status()
            if "charset" not in resp.headers.get("Content-Type", "").lower():
                resp.encoding = resp.apparent_encoding or "utf-8"
            html = resp.text
            if cache:
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(html, encoding="utf-8")
            return html, url
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
            ultimo = e
            if isinstance(e, requests.HTTPError) and e.response is not None \
                    and e.response.status_code < 500:
                raise
            time.sleep(2 * (intento + 1))
    assert ultimo is not None
    raise ultimo
