"""Catálogo de la biblioteca para el plugin de Obsidian.

Genera en ``catalogo/``:

* ``index.json`` — lista de normas con metadatos (sigla, nombre, nº de
  artículos, fechas, hash del contenido, tamaño y ruta del paquete).
* ``<carpeta>.json`` — un paquete por norma con **todas** sus notas
  (``{"archivos": {"ruta/relativa.md": "contenido"}}``), para que el plugin
  descargue una norma completa en una sola petición.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
from pathlib import Path

from .verificar import frontmatter

VERSION_CATALOGO = 1


def generar_catalogo(biblioteca: Path, salida: Path, *, imprimir=print) -> dict:
    salida.mkdir(parents=True, exist_ok=True)
    normas = []
    vigentes = set()
    for carpeta in sorted(p for p in biblioteca.iterdir() if p.is_dir() and not p.name.startswith(".")):
        raiz = carpeta / f"{carpeta.name}.md"
        if not raiz.exists():
            continue
        fm = frontmatter(raiz.read_text(encoding="utf-8"))
        archivos = {}
        for p in sorted(carpeta.rglob("*.md")):
            archivos[p.relative_to(biblioteca).as_posix()] = p.read_text(encoding="utf-8")
        h = hashlib.sha256()
        for ruta, txt in archivos.items():
            h.update(ruta.encode())
            h.update(b"\0")
            h.update(txt.encode())
        paquete = {"version": VERSION_CATALOGO, "carpeta": carpeta.name,
                   "hash": h.hexdigest(), "archivos": archivos}
        datos = json.dumps(paquete, ensure_ascii=False, separators=(",", ":"))
        nombre_paquete = f"{carpeta.name}.json"
        (salida / nombre_paquete).write_text(datos, encoding="utf-8")
        vigentes.add(nombre_paquete)
        normas.append({
            "carpeta": carpeta.name,
            "sigla": fm.get("sigla"),
            "norma": fm.get("norma"),
            "nombre": fm.get("nombre") or fm.get("norma") or carpeta.name,
            "epigrafe": fm.get("epigrafe"),
            "estado": fm.get("estado") or "vigente",
            "articulos": fm.get("articulos"),
            "actualizacion_fuente": fm.get("actualizacion_fuente"),
            "fecha_extraccion": str(fm.get("fecha_extraccion") or ""),
            "fuente": fm.get("fuente"),
            "hash": paquete["hash"],
            "notas": len(archivos),
            "bytes": len(datos.encode()),
            "paquete": nombre_paquete,
        })
    for viejo in salida.glob("*.json"):
        if viejo.name != "index.json" and viejo.name not in vigentes:
            viejo.unlink()
    indice = {"version": VERSION_CATALOGO, "generado": _dt.date.today().isoformat(), "normas": normas}
    (salida / "index.json").write_text(json.dumps(indice, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8")
    imprimir(f"✓ catálogo: {len(normas)} normas en {salida}")
    return indice
